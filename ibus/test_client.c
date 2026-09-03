/*
 * ibus-test-client — headless input context that activates the
 * geist-diktat engine and prints every committed text to stdout.
 *
 * The CI integration test runs this under dbus-run-session next to
 * ibus-daemon and a stubbed engine, then compares the committed lines.
 * Exits 0 after the first commit (or 1 on the timeout).
 */
#include <ibus.h>

#include <stdio.h>
#include <string.h>

static gboolean got_commit = FALSE;

static void on_commit(IBusInputContext *ctx, IBusText *text, gpointer data) {
    (void) ctx;
    (void) data;
    printf("%s\n", ibus_text_get_text(text));
    fflush(stdout);
    got_commit = TRUE;
    ibus_quit();
}

static gboolean on_timeout(gpointer data) {
    (void) data;
    fprintf(stderr, "test_client: timeout waiting for commit\n");
    ibus_quit();
    return G_SOURCE_REMOVE;
}

int main(void) {
    ibus_init();
    IBusBus *bus = ibus_bus_new();
    if (!ibus_bus_is_connected(bus)) {
        fprintf(stderr, "test_client: no ibus daemon\n");
        return 2;
    }

    IBusInputContext *ctx = ibus_bus_create_input_context(bus, "geist-diktat-test");
    if (ctx == NULL) {
        fprintf(stderr, "test_client: create_input_context failed\n");
        return 2;
    }
    g_signal_connect(ctx, "commit-text", G_CALLBACK(on_commit), NULL);
    ibus_input_context_set_capabilities(ctx, IBUS_CAP_FOCUS);
    ibus_input_context_focus_in(ctx);
    ibus_input_context_set_engine(ctx, "geist-diktat");

    g_timeout_add_seconds(110, on_timeout, NULL);
    ibus_main();
    return got_commit ? 0 : 1;
}
