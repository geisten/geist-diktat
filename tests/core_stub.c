/* Execute the unmodified application against a deterministic fake geist API.
 * This tests the actual VAD/lifecycle/output code, not speech recognition. */
#define main diktat_main
#include "../src/diktat.c"
#undef main

struct geist_backend { int unused; };
struct geist_model { int unused; };
struct geist_session { int unused; };
static struct geist_backend backend;
static struct geist_model model;
static struct geist_session session;
static int begins, ends, pushes, polls, decoded, resets, destroyed, loads;
static size_t samples;
static int fail(const char *name) {
    const char *s = getenv("STUB_FAIL");
    return s && strcmp(s, name) == 0;
}
#define STATUS(name) (fail(name) ? GEIST_E_INVALID_ARG : GEIST_OK)
const char *geist_last_create_error(void) { return "injected failure"; }
const char *geist_session_errmsg(const struct geist_session *s) { (void)s; return "injected failure"; }
enum geist_status geist_backend_create(const char *name, const struct geist_backend_opts *o,
        const struct geist_allocator *a, struct geist_backend **out) {
    (void)name; (void)o; (void)a; *out = &backend; return STATUS("backend");
}
void geist_backend_destroy(struct geist_backend *b) { (void)b; destroyed++; }
enum geist_status geist_model_load(const char *p, struct geist_backend *b, struct geist_model **out) {
    (void)p; (void)b; loads++; *out = &model; return STATUS("model");
}
void geist_model_destroy(struct geist_model *m) { (void)m; destroyed++; }
unsigned geist_model_modalities(const struct geist_model *m) { (void)m; return fail("tower") ? 0 : GEIST_MOD_AUDIO; }
enum geist_status geist_session_create(struct geist_model *m, struct geist_backend *b,
        const struct geist_session_opts *o, struct geist_session **out) {
    (void)m; (void)b; (void)o; *out = &session; return STATUS("session");
}
void geist_session_destroy(struct geist_session *s) { (void)s; destroyed++; }
enum geist_status geist_session_reset(struct geist_session *s) { (void)s; resets++; decoded=0; return STATUS("reset"); }
geist_token_t geist_model_bos_token(const struct geist_model *m) { (void)m; return 1; }
geist_token_t geist_model_eos_token(const struct geist_model *m) { (void)m; return 2; }
geist_token_t geist_model_token_by_text(const struct geist_model *m, const char *t) {
    (void)m; return strcmp(t, "<turn|>") == 0 ? 3 : 4;
}
enum geist_status geist_session_tokenize(struct geist_session *s, const char *t, size_t cap,
        geist_token_t ids[static cap], size_t *n) {
    (void)s; (void)t; ids[0]=1; ids[1]=5; *n=2; return STATUS("tokenize");
}
enum geist_status geist_session_pin_prefix(struct geist_session *s, size_t n, const geist_token_t ids[static n]) {
    (void)s; (void)n; (void)ids; return STATUS("prefix");
}
enum geist_status geist_session_prefill_tokens(struct geist_session *s, size_t n, const geist_token_t ids[static n]) {
    (void)s; (void)n; (void)ids; return STATUS("prefill");
}
enum geist_status geist_session_audio_begin(struct geist_session *s) { (void)s; begins++; return STATUS("begin"); }
enum geist_status geist_session_audio_push(struct geist_session *s, size_t n, const int16_t p[static n]) {
    (void)s; (void)p; pushes++; if (fail("push")) return GEIST_E_INVALID_ARG; samples+=n; return GEIST_OK;
}
enum geist_status geist_session_audio_poll(struct geist_session *s) { (void)s; polls++; return STATUS("poll"); }
enum geist_status geist_session_audio_end(struct geist_session *s) { (void)s; ends++; return STATUS("end"); }
enum geist_status geist_session_decode_step(struct geist_session *s, geist_token_t *out) {
    (void)s; decoded++;
    if (fail("meta")) *out=4;
    else if (fail("loop")) *out=5;
    else if (fail("cycle2")) *out=5 + decoded%2;
    else if (fail("cap")) *out=5 + decoded%3;
    else *out=decoded==1 ? 5 : 2;
    return STATUS("decode");
}
const char *geist_session_token_to_str(struct geist_session *s, geist_token_t t) {
    (void)s; (void)t;
    const char *piece=getenv("STUB_PIECE");
    return piece ? piece : "▁Hallo\nWelt\tGrüße\001!";
}
int main(int argc, char **argv) {
    if (argc > 1 && strcmp(argv[1], "--append-boundary") == 0) {
        char line[REPLY_CAP]; size_t n=0;
        char truncated[] = {(char)0xe2, 0};
        append_piece(truncated, line, &n);
        return 0;
    }
    int rc=diktat_main(argc, argv);
    fprintf(stderr,"STATS begins=%d ends=%d pushes=%d polls=%d samples=%zu decoded=%d resets=%d destroyed=%d loads=%d\n",
        begins, ends, pushes, polls, samples, decoded, resets, destroyed, loads);
    return rc;
}
