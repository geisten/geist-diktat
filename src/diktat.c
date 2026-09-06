/*
 * diktat — system-wide dictation core over the public geist API.
 *
 * Reads raw 16 kHz mono s16le PCM from stdin, segments utterances with
 * the same energy VAD as push_to_talk, transcribes each one through the
 * Gemma 4 audio path, and prints ONE LINE of clean text per utterance to
 * stdout (all status goes to stderr). That contract makes it a pipeline
 * stage — the OS integration stays out of tree:
 *
 *   # Wayland: type into the focused window
 *   arecord -f S16_LE -r 16000 -c 1 -t raw | ./diktat model.gguf | python3 runtime/line_sink.py -- wtype --
 *   # X11
 *   arecord ... | ./diktat model.gguf | xargs -d'\n' -I{} xdotool type --clearmodifiers {}
 *   # macOS test run
 *   ffmpeg -f avfoundation -i ":1" -ar 16000 -ac 1 -f s16le - | ./diktat model.gguf 1200
 *
 * GEIST_DIKTAT_PROMPT overrides the instruction (default:
 * "Transcribe this audio." — the best-measured phrasing, 4.2 % WER on
 * the LibriSpeech harness set; see docs/VOICE.md). Decode carries the
 * #267 anti-loop guard, and a reply that opens a thought channel is
 * dropped instead of typed.
 *
 * VAD: identical to push_to_talk — 20 ms frames, opens after 60 ms above
 * threshold, closes after 0.8 s below, threshold as argv[2] (default 300).
 */
#define _POSIX_C_SOURCE 200809L
#include <geist.h>
#include <geist_util.h>

#include <errno.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "trace.h"

static size_t trace_utterance, trace_output, trace_sample;

#define SR 16000
#define FRAME 320       /* 20 ms */
#define OPEN_FRAMES 3   /* speech starts after 60 ms above threshold */
#define CLOSE_FRAMES 40 /* ...ends after 800 ms below it */
#define MIN_UTT (SR / 2)
#define MAX_UTT (28 * SR)
#define PROMPT_CAP 512
#define DECODE_CAP 400
#define REPLY_CAP 4096

static double frame_rms(const int16_t *f) {
    double acc = 0.0;
    for (int i = 0; i < FRAME; i++)
        acc += (double) f[i] * (double) f[i];
    return sqrt(acc / FRAME);
}

/* Process-constant decode setup, filled once in main(). */
static struct {
    geist_token_t bos, eos, end_of_turn, channel;
    const char   *instr;
} cfg;

/* Append one decoded piece to line[], SentencePiece-normalized: U+2581 and
 * newlines become spaces, control bytes are dropped. */
static void append_piece(const char *t, char *line, size_t *len) {
    const unsigned char *p = (const unsigned char *) t;
    size_t left = strlen(t);
    while (left && *len + 1 < REPLY_CAP) {
        if (left >= 3 && p[0] == 0xe2 && p[1] == 0x96 && p[2] == 0x81) {
            line[(*len)++] = ' '; p += 3; left -= 3; continue;
        }
        if (*p < 0x80) {
            if (*p == '\n' || *p == '\r' || *p == '\t') line[(*len)++] = ' ';
            else if (*p >= 0x20) line[(*len)++] = (char) *p;
            p++; left--; continue;
        }
        size_t n = *p >= 0xc2 && *p <= 0xdf ? 2 :
                   *p >= 0xe0 && *p <= 0xef ? 3 :
                   *p >= 0xf0 && *p <= 0xf4 ? 4 : 0;
        if (!n || left < n) break;
        bool valid = true;
        for (size_t i = 1; i < n; i++) valid = valid && (p[i] & 0xc0) == 0x80;
        if ((p[0] == 0xe0 && p[1] < 0xa0) || (p[0] == 0xed && p[1] >= 0xa0) ||
            (p[0] == 0xf0 && p[1] < 0x90) || (p[0] == 0xf4 && p[1] >= 0x90)) valid = false;
        if (!valid) { p++; left--; continue; }
        if (*len + n >= REPLY_CAP) break;
        memcpy(line + *len, p, n); *len += n; p += n; left -= n;
    }
    line[*len] = '\0';
}

/* Audio already streamed into the session; finish the turn and emit the
 * transcript line. */
static int transcribe_utterance(struct geist_session *sess) {
    char          suffix[PROMPT_CAP];
    geist_token_t toks[PROMPT_CAP];
    size_t        n = 0;
    snprintf(suffix, sizeof suffix, "<audio|>\n%s<turn|>\n<|turn>model\n", cfg.instr);
    /* Skip the tokenizer's BOS — the pinned prefix already carries one. */
    const bool   ok   = geist_session_tokenize(sess, suffix, PROMPT_CAP, toks, &n) == GEIST_OK;
    const size_t skip = (ok && n > 0 && toks[0] == cfg.bos) ? 1 : 0;
    if (!ok || geist_session_prefill_tokens(sess, n - skip, toks + skip) != GEIST_OK) {
        fprintf(stderr, "diktat: audio turn failed: %s\n", geist_session_errmsg(sess));
        return 1;
    }

    char          line[REPLY_CAP], raw[REPLY_CAP];
    size_t        raw_len = 0;
    raw[0] = '\0';
    size_t        len     = 0;
    geist_token_t hist[8] = {0};
    line[0]               = '\0';
    for (size_t i = 0; i < DECODE_CAP; i++) {
        geist_token_t tok;
        if (geist_session_decode_step(sess, &tok) != GEIST_OK) {
            fprintf(stderr, "diktat: decode failed: %s\n", geist_session_errmsg(sess));
            return 1;
        }
        if (tok == cfg.eos || tok == cfg.end_of_turn)
            break;
        /* A thought-channel reply is meta text, not dictation — drop the
         * whole utterance rather than typing it. */
        if (i == 0 && cfg.channel >= 0 && tok == cfg.channel) {
            fprintf(stderr, "diktat: model produced meta output, utterance dropped\n");
            return 0;
        }
        /* #267 anti-loop: stop once the last 8 tokens are a period-1/2
         * cycle — keeps a hard clip from typing "big, big, big, ...". */
        hist[i % 8] = tok;
        if (i >= 7) {
            bool cyc2 = true;
            for (size_t k = i - 5; k <= i; k++)
                cyc2 = cyc2 && hist[k % 8] == hist[(k - 2) % 8];
            if (cyc2)
                break;
        }
        const char *t = geist_session_token_to_str(sess, tok);
        if (t != nullptr) {
            /* Tokens may divide a UTF-8 code point. Normalize the joined
             * bounded byte stream, then discard only an incomplete tail. */
            size_t count = strlen(t);
            if (count > REPLY_CAP - 1 - raw_len) count = REPLY_CAP - 1 - raw_len;
            memcpy(raw + raw_len, t, count); raw_len += count; raw[raw_len] = '\0';
        }
    }

    append_piece(raw, line, &len);

    /* Trim the leading SentencePiece space; emit exactly one line. */
    const char *out = line[0] == ' ' ? line + 1 : line;
    if (out[0] != '\0') {
        diktat_trace("core", "output_ready", trace_utterance, trace_output+1, trace_sample);
        if (printf("%s\n", out) < 0 || fflush(stdout) != 0) {
            perror("diktat: output"); return 1;
        }
        diktat_trace("core", "output_emitted", trace_utterance, ++trace_output, trace_sample);
    }
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2 || argc > 3) {
        fprintf(stderr,
                "usage: arecord -f S16_LE -r 16000 -c 1 -t raw | %s <model.gguf> [rms-threshold]\n",
                argv[0]);
        return 2;
    }
    double rms_thr = 300.0;
    if (argc > 2) {
        char *end = NULL;
        errno = 0;
        rms_thr = strtod(argv[2], &end);
        if (!argv[2][0] || strspn(argv[2], "0123456789.eE+-") != strlen(argv[2]) ||
            end == argv[2] || *end || errno || !(rms_thr > 0 && rms_thr <= 32768)) {
            fprintf(stderr, "diktat: RMS threshold must be a number in (0, 32768]\n");
            return 2;
        }
    }
    cfg.instr = getenv("GEIST_DIKTAT_PROMPT");
    if (cfg.instr == nullptr)
        cfg.instr = "Transcribe this audio.";

    struct geist_backend *be = nullptr;
    if (geist_backend_create("cpu_neon", nullptr, nullptr, &be) != GEIST_OK &&
        geist_backend_create("cpu_x86", nullptr, nullptr, &be) != GEIST_OK &&
        geist_backend_create("cpu_scalar", nullptr, nullptr, &be) != GEIST_OK) {
        fprintf(stderr, "backend create failed: %s\n", geist_last_create_error());
        return 1;
    }
    diktat_trace("core", "model_load_start", 0, 0, 0);
    struct geist_model *model = nullptr;
    if (geist_model_load(argv[1], be, &model) != GEIST_OK) {
        fprintf(stderr, "model_load failed: %s\n", geist_last_create_error());
        geist_backend_destroy(be);
        return 1;
    }
    if ((geist_model_modalities(model) & GEIST_MOD_AUDIO) == 0) {
        fprintf(stderr, "this model instance cannot hear (no audio tower found)\n");
        geist_model_destroy(model);
        geist_backend_destroy(be);
        return 1;
    }

    struct geist_session_opts opts = {.max_seq_len = 2048};
    struct geist_session     *sess = nullptr;
    if (geist_session_create(model, be, &opts, &sess) != GEIST_OK) {
        fprintf(stderr, "session_create failed\n");
        geist_model_destroy(model);
        geist_backend_destroy(be);
        return 1;
    }
    cfg.bos         = geist_model_bos_token(model);
    cfg.eos         = geist_model_eos_token(model);
    cfg.end_of_turn = geist_model_token_by_text(model, "<turn|>");
    cfg.channel     = geist_model_token_by_text(model, "<|channel>");

    {
        geist_token_t prefix[PROMPT_CAP];
        size_t        n_prefix = 0;
        if (geist_session_tokenize(
                    sess, "<bos><|turn>user\n<|audio>", PROMPT_CAP, prefix, &n_prefix) != GEIST_OK ||
            geist_session_pin_prefix(sess, n_prefix, prefix) != GEIST_OK) {
            fprintf(stderr, "pin_prefix failed\n");
            geist_session_destroy(sess);
            geist_model_destroy(model);
            geist_backend_destroy(be);
            return 1;
        }
    }

    diktat_trace("core", "model_ready", 0, 0, 0);
    fprintf(stderr, "diktat: listening (VAD threshold %.0f RMS, Ctrl-C to quit)...\n", rms_thr);

    /* Same streaming VAD loop as push_to_talk: push PCM while the user
     * speaks, poll injects ready soft tokens, end() pays only the tail. */
    int16_t frame[FRAME];
    int16_t pending[OPEN_FRAMES][FRAME];
    size_t pending_sizes[OPEN_FRAMES];
    size_t pushed = 0, trailing = 0, received_samples = 0;
    int loud = 0, quiet = 0, result = 0;
    bool in_speech = false;
    size_t bytes;
    while ((bytes = fread(frame, 1, sizeof frame, stdin)) != 0) {
        if (bytes % sizeof(int16_t)) {
            fprintf(stderr, "diktat: incomplete PCM16 sample\n"); result = 1; break;
        }
        const size_t n = bytes / sizeof(int16_t);
        received_samples += n;
        memset(frame + n, 0, sizeof frame - bytes);
        const bool is_loud = frame_rms(frame) > rms_thr;
        if (is_loud) trace_sample = received_samples;
        if (!in_speech) {
            memcpy(pending[loud], frame, sizeof frame);
            pending_sizes[loud] = n;
            loud = is_loud ? loud + 1 : 0;
            if (loud < OPEN_FRAMES) continue;
            if (geist_session_reset(sess) != GEIST_OK || geist_session_audio_begin(sess) != GEIST_OK) {
                result = 1; break;
            }
            trace_utterance++;
            in_speech = true; quiet = 0; pushed = trailing = 0;
            for (int i = 0; i < OPEN_FRAMES - 1; i++) {
                if (geist_session_audio_push(sess, pending_sizes[i], pending[i]) != GEIST_OK) {
                    result = 1; break;
                }
                pushed += pending_sizes[i];
            }
            if (result) break;
        }
        if (geist_session_audio_push(sess, n, frame) != GEIST_OK ||
            geist_session_audio_poll(sess) != GEIST_OK) { result = 1; break; }
        pushed += n;
        quiet = is_loud ? 0 : quiet + 1;
        trailing = is_loud ? 0 : trailing + n;
        if (quiet >= CLOSE_FRAMES || pushed >= MAX_UTT) {
            diktat_trace("core", "decode_start", trace_utterance, trace_output, trace_sample);
            if (geist_session_audio_end(sess) != GEIST_OK) { result = 1; break; }
            if (pushed - trailing >= MIN_UTT) {
                fprintf(stderr, "diktat: [%.1f s]\n", (double) pushed / SR);
                result = transcribe_utterance(sess);
            } else if (geist_session_reset(sess) != GEIST_OK) result = 1;
            diktat_trace("core", "decode_end", trace_utterance, trace_output, trace_sample);
            in_speech = false; loud = 0;
            if (result) break;
        }
    }
    if (ferror(stdin)) { perror("diktat: input"); result = 1; }
    if (!result && in_speech) {
        diktat_trace("core", "decode_start", trace_utterance, trace_output, trace_sample);
        if (geist_session_audio_end(sess) != GEIST_OK) result = 1;
        else if (pushed - trailing >= MIN_UTT) result = transcribe_utterance(sess);
        diktat_trace("core", "decode_end", trace_utterance, trace_output, trace_sample);
    }
    diktat_trace("core", "input_summary", trace_utterance, trace_output, received_samples);
    if (result) fprintf(stderr, "diktat: recognition failed: %s\n", geist_session_errmsg(sess));

    geist_session_destroy(sess);
    geist_model_destroy(model);
    geist_backend_destroy(be);
    return result;
}
