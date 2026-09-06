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
 *   arecord -f S16_LE -r 16000 -c 1 -t raw | ./diktat model.gguf | wtype -
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
#include <geist.h>
#include <geist_util.h>

#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

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

/* Byte length of the UTF-8 sequence starting at c. A stray continuation
 * byte reports 1 and is dropped as a control byte below. */
static size_t utf8_len(unsigned char c) {
    if (c < 0x80)
        return 1;
    if ((c & 0xE0) == 0xC0)
        return 2;
    if ((c & 0xF0) == 0xE0)
        return 3;
    if ((c & 0xF8) == 0xF0)
        return 4;
    return 1;
}

/* Append one decoded piece to line[], SentencePiece-normalized: U+2581 and
 * newlines become spaces, control bytes are dropped.
 *
 * Characters are copied whole or not at all. Byte-at-a-time copying let the
 * REPLY_CAP cut land inside a multi-byte character, so a reply that happened
 * to fill the buffer emitted invalid UTF-8 — and the old U+2581 test read
 * p[1] and p[2] before checking that p[0] was not the last byte of the
 * piece, which reads past the terminator on a piece ending in 0xE2. */
static void append_piece(const char *t, char *line, size_t *len) {
    for (const char *p = t; *p != '\0';) {
        const unsigned char c   = (unsigned char) *p;
        const size_t        seq = utf8_len(c);
        /* A sequence the piece cuts short is not a character. */
        if (strnlen(p, seq) < seq)
            break;

        if (seq == 3 && c == 0xE2 && (unsigned char) p[1] == 0x96 &&
            (unsigned char) p[2] == 0x81) { /* U+2581, the word marker */
            if (*len + 1 >= REPLY_CAP)
                break;
            line[(*len)++] = ' ';
            p += 3;
        } else if (seq == 1) {
            if (c == '\n' || c == '\r' || c == '\t') {
                if (*len + 1 >= REPLY_CAP)
                    break;
                line[(*len)++] = ' ';
            } else if (c >= 0x20) {
                if (*len + 1 >= REPLY_CAP)
                    break;
                line[(*len)++] = (char) c;
            }
            p += 1;
        } else {
            if (*len + seq >= REPLY_CAP)
                break;
            memcpy(line + *len, p, seq);
            *len += seq;
            p += seq;
        }
    }
    line[*len] = '\0';
}

/* Audio already streamed into the session; finish the turn and emit the
 * transcript line. Returns 0, or 1 when the engine failed — a transcription
 * that did not happen must not leave the process exiting 0. */
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

    char          line[REPLY_CAP];
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
            return 0; /* dropped on purpose, not a failure */
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
        if (t != nullptr)
            append_piece(t, line, &len);
    }

    /* Trim the leading SentencePiece space; emit exactly one line. */
    const char *out = line[0] == ' ' ? line + 1 : line;
    if (out[0] != '\0') {
        printf("%s\n", out);
        fflush(stdout);
    }
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) {
        fprintf(stderr,
                "usage: arecord -f S16_LE -r 16000 -c 1 -t raw | %s <model.gguf> [rms-threshold]\n",
                argv[0]);
        return 2;
    }
    /* atof() turned "abc" into 0.0 and accepted "nan", "-1" and "300junk" —
     * a threshold of 0 opens the VAD on silence and never closes it. Reject
     * before the model is loaded, so a typo costs no gigabytes. */
    double rms_thr = 300.0;
    if (argc > 2) {
        char *end = nullptr;
        rms_thr   = strtod(argv[2], &end);
        if (end == argv[2] || *end != '\0' || !isfinite(rms_thr) || rms_thr <= 0.0) {
            fprintf(stderr, "diktat: rms-threshold must be a positive number, got '%s'\n", argv[2]);
            return 2;
        }
    }
    cfg.instr            = getenv("GEIST_DIKTAT_PROMPT");
    if (cfg.instr == nullptr)
        cfg.instr = "Transcribe this audio.";

    /* cpu_scalar is the fallback of last resort, not the x86 backend: the
     * list went neon -> scalar, so every x86 host quietly ran unaccelerated. */
    struct geist_backend *be = nullptr;
    if (geist_backend_create("cpu_neon", nullptr, nullptr, &be) != GEIST_OK &&
        geist_backend_create("cpu_x86", nullptr, nullptr, &be) != GEIST_OK &&
        geist_backend_create("cpu_scalar", nullptr, nullptr, &be) != GEIST_OK) {
        fprintf(stderr, "backend create failed: %s\n", geist_last_create_error());
        return 1;
    }
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
                    sess, "<bos><|turn>user\n<|audio>", PROMPT_CAP, prefix, &n_prefix) !=
                    GEIST_OK ||
            geist_session_pin_prefix(sess, n_prefix, prefix) != GEIST_OK) {
            fprintf(stderr, "pin_prefix failed\n");
            geist_session_destroy(sess);
            geist_model_destroy(model);
            geist_backend_destroy(be);
            return 1;
        }
    }

    fprintf(stderr, "diktat: listening (VAD threshold %.0f RMS, Ctrl-C to quit)...\n", rms_thr);

    /* Same streaming VAD loop as push_to_talk: push PCM while the user
     * speaks, poll injects ready soft tokens, end() pays only the tail. */
    int16_t frame[FRAME];
    int16_t pending[OPEN_FRAMES][FRAME];
    size_t  pushed = 0;
    int     loud = 0, quiet = 0;
    bool    in_speech = false;

    /* Every engine call below is checked: failures used to be logged and
     * then ignored, so a session that had stopped working still exited 0
     * and the pipeline downstream saw a clean run producing no text. */
    int rc = 0;
    for (;;) {
        const size_t got = fread(frame, sizeof(int16_t), FRAME, stdin);
        if (got < FRAME) {
            /* Short read means EOF. The tail still counts: a final partial
             * frame was dropped outright, and so was the whole last
             * utterance when the mic closed while it was still open. */
            if (in_speech && got > 0) {
                if (geist_session_audio_push(sess, got, frame) != GEIST_OK) {
                    fprintf(stderr, "audio_push failed: %s\n", geist_session_errmsg(sess));
                    rc = 1;
                } else {
                    pushed += got;
                }
            }
            break;
        }
        const bool is_loud = frame_rms(frame) > rms_thr;
        if (!in_speech) {
            memcpy(pending[loud % OPEN_FRAMES], frame, sizeof frame);
            loud = is_loud ? loud + 1 : 0;
            if (loud < OPEN_FRAMES)
                continue;
            in_speech = true;
            quiet     = 0;
            pushed    = 0;
            if (geist_session_reset(sess) != GEIST_OK) {
                fprintf(stderr, "session_reset failed: %s\n", geist_session_errmsg(sess));
                rc = 1;
                break;
            }
            if (geist_session_audio_begin(sess) != GEIST_OK) {
                fprintf(stderr, "audio_begin failed: %s\n", geist_session_errmsg(sess));
                rc = 1;
                break;
            }
            for (int i = 0; i < OPEN_FRAMES - 1 && rc == 0; i++) {
                if (geist_session_audio_push(sess, FRAME, pending[i]) != GEIST_OK) {
                    fprintf(stderr, "audio_push failed: %s\n", geist_session_errmsg(sess));
                    rc = 1;
                } else {
                    pushed += FRAME;
                }
            }
            if (rc != 0)
                break;
        }
        if (pushed + FRAME <= MAX_UTT) {
            if (geist_session_audio_push(sess, FRAME, frame) != GEIST_OK) {
                fprintf(stderr, "audio_push failed: %s\n", geist_session_errmsg(sess));
                rc = 1;
                break;
            }
            pushed += FRAME;
            if (geist_session_audio_poll(sess) != GEIST_OK) {
                fprintf(stderr, "audio_poll failed: %s\n", geist_session_errmsg(sess));
                rc = 1;
                break;
            }
        }
        quiet = is_loud ? 0 : quiet + 1;
        if (quiet >= CLOSE_FRAMES || pushed + FRAME > MAX_UTT) {
            in_speech               = false;
            loud                    = 0;
            const size_t speech_len = pushed - (size_t) quiet * FRAME;
            if (geist_session_audio_end(sess) != GEIST_OK) {
                fprintf(stderr, "audio_end failed: %s\n", geist_session_errmsg(sess));
                rc = 1;
                break;
            }
            if (speech_len >= MIN_UTT) {
                fprintf(stderr, "diktat: [%.1f s]\n", (double) pushed / SR);
                if ((rc = transcribe_utterance(sess)) != 0)
                    break;
            } else if (geist_session_reset(sess) != GEIST_OK) {
                fprintf(stderr, "session_reset failed: %s\n", geist_session_errmsg(sess));
                rc = 1;
                break;
            }
        }
    }

    /* Still mid-utterance at EOF: close the turn and transcribe it. */
    if (rc == 0 && in_speech) {
        const size_t speech_len = pushed - (size_t) quiet * FRAME;
        if (geist_session_audio_end(sess) != GEIST_OK) {
            fprintf(stderr, "audio_end failed: %s\n", geist_session_errmsg(sess));
            rc = 1;
        } else if (speech_len >= MIN_UTT) {
            fprintf(stderr, "diktat: [%.1f s]\n", (double) pushed / SR);
            rc = transcribe_utterance(sess);
        }
    }

    geist_session_destroy(sess);
    geist_model_destroy(model);
    geist_backend_destroy(be);
    return rc;
}
