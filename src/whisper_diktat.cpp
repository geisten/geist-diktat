// Resident CPU candidate: PCM16LE stdin -> one final UTF-8 line per utterance.
// Model/state live for the session. No audio files or subprocess per utterance.
#include <whisper.h>
#include "trace.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <cerrno>
#include <cmath>
#include <condition_variable>
#include <csignal>
#include <deque>
#include <memory>
#include <mutex>
#include <poll.h>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

namespace {
constexpr size_t frame_samples=320, max_samples=28*16000, queue_frames=50;
static_assert(std::atomic<int>::is_always_lock_free, "signal cancellation must be lock-free");
std::atomic<int> cancelled{0};
void cancel(int sig) { cancelled=sig; }
int integer_env(const char *name, int fallback, int maximum) {
    const char *s=getenv(name); if (!s) return fallback;
    char *end=nullptr; errno=0; long n=strtol(s,&end,10);
    if (errno || end==s || *end || n<1 || n>maximum) throw std::runtime_error(std::string("invalid ")+name);
    return static_cast<int>(n);
}
struct Frame { std::array<float,frame_samples> pcm{}; size_t size=0; };
// One second of lookahead. Backpressure is lossless; the external supervisor
// still owns the overload policy. This queue cannot conceal unbounded lag.
class Input {
    std::mutex mutex;
    std::condition_variable changed;
    std::deque<Frame> frames;
    std::thread reader;
    bool eof=false;
    std::atomic<bool> stopped{false};
    std::atomic<int> failure{0};
    size_t received=0, peak=0;
    void read_loop() {
        std::array<unsigned char,640> raw{}; size_t used=0;
        while (!stopped && !cancelled) {
            {
                std::unique_lock<std::mutex> lock(mutex);
                changed.wait_for(lock,std::chrono::milliseconds(50),[&]{return frames.size()<queue_frames || stopped.load();});
                if (frames.size()>=queue_frames) continue;
            }
            struct pollfd fd{STDIN_FILENO,POLLIN,0};
            int status=poll(&fd,1,50);
            if (status<0) { if (errno==EINTR) continue; failure=74; break; }
            if (!status) continue;
            ssize_t n=read(STDIN_FILENO,raw.data()+used,raw.size()-used);
            if (n<0) { if (errno==EINTR || errno==EAGAIN) continue; failure=74; break; }
            used+=static_cast<size_t>(n); received+=static_cast<size_t>(n);
            if (!n && used%2) { failure=74; break; }
            if (used==raw.size() || (!n && used)) {
                Frame frame; frame.size=used/2;
                for (size_t i=0;i<frame.size;++i) {
                    int value=raw[2*i] | (static_cast<unsigned>(raw[2*i+1])<<8);
                    if (value>=32768) value-=65536;
                    frame.pcm[i]=static_cast<float>(value)/32768.0f;
                }
                { std::lock_guard<std::mutex> lock(mutex); frames.push_back(frame); peak=std::max(peak,frames.size()); }
                changed.notify_all(); used=0;
            }
            if (!n) break;
        }
        { std::lock_guard<std::mutex> lock(mutex); eof=true; }
        changed.notify_all();
    }
public:
    Input() { reader=std::thread([this]{read_loop();}); }
    ~Input() { stop(); }
    bool aborted() const { return cancelled || failure.load()!=0; }
    int error() const { return failure.load(); }
    bool next(Frame &frame) {
        std::unique_lock<std::mutex> lock(mutex);
        while (frames.empty() && !eof && !aborted()) changed.wait_for(lock,std::chrono::milliseconds(50));
        if (aborted() || frames.empty()) return false;
        frame=frames.front(); frames.pop_front(); changed.notify_all(); return true;
    }
    void stop() { stopped=true; changed.notify_all(); if (reader.joinable()) reader.join(); }
    void summary() { // only after stop/join
        diktat_trace("whisper_input","received_samples",0,0,received/2);
        diktat_trace("whisper_input","peak_queue_samples",0,0,peak*frame_samples);
    }
};
bool abort_decode(void *data) { return static_cast<Input *>(data)->aborted(); }
std::string line_text(whisper_context *ctx) {
    std::string line; bool space=false;
    for (int i=0;i<whisper_full_n_segments(ctx);++i) {
        const char *text=whisper_full_get_segment_text(ctx,i);
        if (!text) throw std::runtime_error("missing segment text");
        for (const unsigned char *p=reinterpret_cast<const unsigned char *>(text);*p;++p) {
            if (*p==' ' || *p=='\n' || *p=='\r' || *p=='\t') { space=!line.empty(); continue; }
            if (*p<32 || *p==127) continue;
            if (space) { line+=' '; space=false; }
            line+=static_cast<char>(*p);
            if (line.size()>65536) throw std::runtime_error("transcript exceeds line limit");
        }
    }
    return line;
}
int session(whisper_context *ctx, whisper_full_params params, double threshold) {
    Input input; params.abort_callback=abort_decode; params.abort_callback_user_data=&input;
    std::vector<float> pcm; pcm.reserve(max_samples);
    std::vector<float> pre; pre.reserve(3*frame_samples);
    bool active=false; size_t quiet=0, loud_frames=0, total=0, last_loud=0, utterance=0, output=0;
    auto decode=[&]() {
        if (pcm.size()<8000 || input.aborted()) return;
        ++utterance; diktat_trace("core","decode_start",utterance,output,last_loud);
        int rc=whisper_full(ctx,params,pcm.data(),static_cast<int>(pcm.size()));
        diktat_trace("core","decode_end",utterance,output,last_loud);
        if (input.aborted()) return;
        if (rc) throw std::runtime_error("whisper decode failed: "+std::to_string(rc));
        std::string line=line_text(ctx);
        if (line.empty() || input.aborted()) return;
        diktat_trace("core","output_ready",utterance,output+1,last_loud);
        if (printf("%s\n",line.c_str())<0 || fflush(stdout)!=0) throw std::runtime_error("stdout write failed");
        diktat_trace("core","output_emitted",utterance,++output,last_loud);
    };
    try {
        Frame frame;
        while (input.next(frame)) {
            total+=frame.size;
            double energy=0; for (size_t i=0;i<frame.size;++i) energy+=double(frame.pcm[i])*frame.pcm[i];
            bool loud=std::sqrt(energy/frame_samples)*32768>threshold;
            if (loud) last_loud=total;
            if (!active) {
                if (!loud) { pre.clear(); loud_frames=0; continue; }
                pre.insert(pre.end(),frame.pcm.begin(),frame.pcm.begin()+frame.size);
                if (++loud_frames<3) continue;
                pcm.assign(pre.begin(),pre.end()); pre.clear(); loud_frames=0; active=true; quiet=0;
            } else pcm.insert(pcm.end(),frame.pcm.begin(),frame.pcm.begin()+frame.size);
            quiet=loud?0:quiet+1;
            if (quiet>=40 || pcm.size()>=max_samples) { decode(); pcm.clear(); active=false; quiet=0; }
        }
        if (active) decode();
        input.stop(); input.summary();
        diktat_trace("core","input_summary",utterance,output,total);
        if (input.error()) { fprintf(stderr,"diktat: invalid or failed PCM input\n"); return input.error(); }
        return cancelled?128+cancelled:0;
    } catch (...) { input.stop(); throw; }
}
}
int main(int argc,char **argv) {
    try {
        if (argc<2 || argc>3) throw std::runtime_error("usage: diktat-whisper MODEL [RMS]");
        char *end=nullptr; errno=0;
        double rms=argc==3?strtod(argv[2],&end):300;
        if (errno || (argc==3 && (end==argv[2] || *end)) || !std::isfinite(rms) || rms<=0 || rms>32768)
            throw std::runtime_error("invalid RMS");
        int threads=integer_env("OMP_NUM_THREADS",4,256), beam=integer_env("GEIST_WHISPER_BEAM_SIZE",5,8);
        struct sigaction action{}; action.sa_handler=cancel; sigemptyset(&action.sa_mask);
        sigaction(SIGTERM,&action,nullptr); sigaction(SIGINT,&action,nullptr); signal(SIGPIPE,SIG_IGN);
        auto options=whisper_context_default_params(); options.use_gpu=false; options.flash_attn=true;
        diktat_trace("core","model_load_start",0,0,0);
        std::unique_ptr<whisper_context,decltype(&whisper_free)> ctx(whisper_init_from_file_with_params(argv[1],options),whisper_free);
        if (cancelled) return 128+cancelled;
        if (!ctx) throw std::runtime_error("model_load failed");
        auto params=whisper_full_default_params(WHISPER_SAMPLING_GREEDY);
        params.strategy=beam>1?WHISPER_SAMPLING_BEAM_SEARCH:WHISPER_SAMPLING_GREEDY;
        params.beam_search.beam_size=beam; params.n_threads=threads;
        params.language="de"; params.translate=false; params.detect_language=false;
        params.no_context=true; params.no_timestamps=true;
        params.print_realtime=false; params.print_progress=false; params.print_timestamps=false; params.print_special=false;
        diktat_trace("core","model_ready",0,0,0);
        fprintf(stderr,"diktat: listening (resident whisper CPU; threads=%d beam=%d)\n",threads,beam); fflush(stderr);
        return session(ctx.get(),params,rms);
    } catch (const std::exception &error) {
        fprintf(stderr,"diktat: %s\n",error.what()); return cancelled?128+cancelled:1;
    }
}
