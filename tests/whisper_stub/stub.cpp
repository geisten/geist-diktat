#include "whisper.h"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <thread>
#include <chrono>
#include <string>
struct whisper_context { int calls=0; };
static void record(const char *event,int value=0) {
    if (const char *path=getenv("STUB_LOG")) {
        FILE *f=fopen(path,"a"); if (!f) abort(); fprintf(f,"%s %d\n",event,value); fclose(f);
    }
}
whisper_context_params whisper_context_default_params() { return {}; }
whisper_context *whisper_init_from_file_with_params(const char *,whisper_context_params p) {
    record("load"); if (p.use_gpu || !p.flash_attn) abort();
    return getenv("STUB_LOAD_FAIL")?nullptr:new whisper_context;
}
void whisper_free(whisper_context *p) { record("free",p->calls); delete p; }
whisper_full_params whisper_full_default_params(whisper_sampling_strategy s) { whisper_full_params p; p.strategy=s; return p; }
int whisper_full(whisper_context *ctx,whisper_full_params p,const float *audio,int n) {
    ++ctx->calls; record("decode",n);
    if (strcmp(p.language,"de") || !p.no_context || !p.no_timestamps || p.translate || p.detect_language ||
        p.print_realtime || p.print_progress || p.print_timestamps || p.print_special || !p.abort_callback || p.n_threads<1) abort();
    for (int i=0;i<n;++i) if (audio[i]<-1 || audio[i]>=1) abort();
    record("first_sample",int(audio[0]*32768)); record("beam",p.beam_search.beam_size);
    if (getenv("STUB_BLOCK")) {
        fprintf(stderr,"stub: decoding\n"); fflush(stderr);
        for (int i=0;i<200;++i) {
            if (p.abort_callback(p.abort_callback_user_data)) { record("aborted"); return 1; }
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
    }
    return getenv("STUB_DECODE_FAIL")?7:0;
}
int whisper_full_n_segments(whisper_context *) { return getenv("STUB_EMPTY")?0:2; }
const char *whisper_full_get_segment_text(whisper_context *,int index) {
    static std::string large(65537,'x');
    if (getenv("STUB_LARGE")) return large.c_str();
    return index?" Welt\r\nGrüße!\t ":" Hallo";
}
