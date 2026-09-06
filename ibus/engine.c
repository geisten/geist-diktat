/*
 * ibus-engine-geist-diktat — dictation as an IBus input source.
 *
 * The engine owns the capture lifecycle: selecting the input source
 * (enable) spawns the dictation pipeline; switching away (disable)
 * kills it. Focus loss also stops capture, and protected input fields
 * never start it. Each transcript line is committed through the standard
 * IME protocol, so every IBus-aware app (GTK, Qt, Electron, VTE
 * terminals) receives it — no uinput, no root.
 *
 * Run modes:
 *   --ibus       spawned by ibus-daemon via the component XML
 *   (standalone) registers its component programmatically — the test
 *                and development mode
 *
 * The pipeline is /usr/bin/geist-diktat run, with the per-user
 * model from ~/.local/share/geist-diktat and GEIST_DIKTAT_RMS as the VAD
 * threshold. GEIST_DIKTAT_CMD replaces the whole pipeline but exists only
 * in the test build (-DGEIST_DIKTAT_TEST_HOOKS, target
 * ibus-engine-geist-diktat-test) — the shipped engine must not take its
 * command line from the environment.
 *
 * ponytail: the pipeline (and its model load, seconds) starts per
 * enable. A resident daemon with a warm model is the upgrade path if
 * source-switch latency matters.
 */
#define _POSIX_C_SOURCE 200809L
#include <ibus.h>
#include "../src/trace.h"

#include <glib-unix.h>

#include <errno.h>
#include <sys/wait.h>
#include <signal.h>
#include <string.h>
#include <unistd.h>

#define ENGINE_NAME "geist-diktat"
#define BUS_NAME "org.freedesktop.IBus.GeistDiktat"

/* ---- engine type ------------------------------------------------------ */

/* Classic GObject boilerplate — G_DECLARE_FINAL_TYPE needs autoptr
 * support on the parent type, which libibus does not define for
 * IBusEngine. */
typedef struct _GeistEngine GeistEngine;
typedef struct _GeistEngineClass GeistEngineClass;

#define GEIST_TYPE_ENGINE (geist_engine_get_type())
#define GEIST_ENGINE(obj) (G_TYPE_CHECK_INSTANCE_CAST((obj), GEIST_TYPE_ENGINE, GeistEngine))

GType geist_engine_get_type(void);

struct _GeistEngineClass {
    IBusEngineClass parent;
};

struct _GeistEngine {
    IBusEngine parent;
    GPid       pid;   /* pipeline process group leader; 0 = not running */
    guint      child_watch;
    gboolean enabled, focused, protected_input;
    size_t trace_output;
    guint      watch; /* GIOChannel source id */
    GIOChannel *out;
    IBusPropList *props;
    IBusProperty *state_prop;
};

G_DEFINE_TYPE(GeistEngine, geist_engine, IBUS_TYPE_ENGINE)

/* The single live engine instance (one per ibus engine process) — the
 * SIGTERM handler must reach it to take the pipeline process group down
 * with the engine. */
static struct _GeistEngine *g_active_engine = NULL;

/* The VAD threshold reaches /bin/sh, so accept it only as a plain
 * positive number — never interpolate the raw env value. */
static double pipeline_rms(void) {
    const char *s = g_getenv("GEIST_DIKTAT_RMS");
    if (s == NULL || s[0] == '\0') {
        return 300.0;
    }
    char  *end = NULL;
    double v   = g_ascii_strtod(s, &end);
    if (end == s || *end != '\0' || !(v > 0.0 && v < 1e6)) {
        g_warning("geist-diktat: ignoring non-numeric GEIST_DIKTAT_RMS=%s", s);
        return 300.0;
    }
    return v;
}

static gchar *pipeline_cmd(void) {
#ifdef GEIST_DIKTAT_TEST_HOOKS
    /* Test-only pipeline override. Deliberately NOT compiled into the
     * packaged engine: an env var must not choose what the IME runs. */
    const char *override = g_getenv("GEIST_DIKTAT_CMD");
    if (override != NULL && override[0] != '\0') {
        return g_strdup(override);
    }
#endif
    return g_strdup_printf("exec /usr/bin/geist-diktat run %.6g", pipeline_rms());
}

static void update_state(GeistEngine *e, const char *label) {
    if (e->state_prop == NULL) {
        return;
    }
    ibus_property_set_label(e->state_prop, ibus_text_new_from_string(label));
    ibus_engine_update_property(IBUS_ENGINE(e), e->state_prop);
}

/* One transcript line arrived — commit it followed by a space, so
 * consecutive utterances flow like typed text. */
static void close_output(GeistEngine *e) {
    if (e->watch) { g_source_remove(e->watch); e->watch = 0; }
    if (e->out) { g_io_channel_unref(e->out); e->out = NULL; }
}

static gboolean on_pipeline_line(GIOChannel *ch, GIOCondition cond, gpointer data) {
    GeistEngine *e = data;
    for (;;) {
        gchar *line = NULL;
        GError *error = NULL;
        GIOStatus status = g_io_channel_read_line(ch, &line, NULL, NULL, &error);
        if (status == G_IO_STATUS_NORMAL && line) {
            g_strchomp(line);
            if (line[0] && !e->protected_input) {
                gchar *text = g_strconcat(line, " ", NULL);
                ibus_engine_commit_text(IBUS_ENGINE(e), ibus_text_new_from_string(text));
                diktat_trace("ibus", "commit_requested", 0, ++e->trace_output, 0);
                g_free(text);
            }
            g_free(line); continue;
        }
        g_free(line);
        if (error) { g_warning("diktat: output failed: %s", error->message); g_clear_error(&error); }
        if (status == G_IO_STATUS_AGAIN && !(cond & (G_IO_HUP | G_IO_ERR))) return TRUE;
        e->watch = 0;
        if (e->out) { g_io_channel_unref(e->out); e->out = NULL; }
        return FALSE;
    }
}

static void on_child_exit(GPid pid, gint status, gpointer data) {
    GeistEngine *e = data;
    if (e->pid != pid) return;
    e->pid = 0; e->child_watch = 0;
    g_spawn_close_pid(pid); /* GLib's child watch has already reaped it. */
    update_state(e, status == 0 ? "diktat: beendet" : "diktat: Aufnahme/Erkennung fehlgeschlagen");
    /* The output watch drains any final lines before releasing its channel. */
}

/* Child setup: own process group, so stopping kills arecord AND diktat. */
static void child_setpgid(gpointer user_data) {
    (void) user_data;
    setpgid(0, 0);
}

static void pipeline_start(GeistEngine *e) {
    if (e->pid != 0) {
        return;
    }
    close_output(e);
    e->trace_output = 0;
    gchar *cmd    = pipeline_cmd();
    gchar *argv[] = {"/bin/sh", "-c", cmd, NULL};
    gint   out_fd = -1;
    GError *err   = NULL;
    if (!g_spawn_async_with_pipes(NULL, argv, NULL,
                                  G_SPAWN_SEARCH_PATH | G_SPAWN_DO_NOT_REAP_CHILD,
                                  child_setpgid, NULL, &e->pid, NULL, &out_fd, NULL, &err)) {
        g_warning("geist-diktat: pipeline spawn failed: %s", err->message);
        g_clear_error(&err);
        e->pid = 0;
        g_free(cmd);
        return;
    }
    g_free(cmd);
    e->out = g_io_channel_unix_new(out_fd);
    g_io_channel_set_close_on_unref(e->out, TRUE);
    g_io_channel_set_flags(e->out, g_io_channel_get_flags(e->out) | G_IO_FLAG_NONBLOCK, NULL);
    e->child_watch = g_child_watch_add(e->pid, on_child_exit, e);
    e->watch = g_io_add_watch(e->out, G_IO_IN | G_IO_HUP | G_IO_ERR, on_pipeline_line, e);
    update_state(e, "diktat: Aufnahme gestartet");
}

static void pipeline_stop(GeistEngine *e) {
    close_output(e);
    if (e->child_watch) { g_source_remove(e->child_watch); e->child_watch = 0; }
    GPid pid = e->pid; e->pid = 0;
    if (pid) {
        if (kill(-pid, SIGTERM) != 0 && errno == ESRCH) kill(pid, SIGTERM);
        int status = 0;
        gboolean reaped = FALSE;
        for (int i = 0; i < 150; i++) {
            pid_t r = waitpid(pid, &status, WNOHANG);
            if (r == pid || (r < 0 && errno == ECHILD)) { reaped = TRUE; break; }
            g_usleep(10000);
        }
        if (!reaped) {
            kill(-pid, SIGKILL); kill(pid, SIGKILL);
            while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {}
        }
        /* Reaping the leader alone does not kill a stubborn descendant. */
        kill(-pid, SIGKILL);
        g_spawn_close_pid(pid);
    }
    update_state(e, "diktat: aus");
}

/* ---- IBusEngine vfuncs ------------------------------------------------ */

static void geist_engine_enable(IBusEngine *engine) {
    GeistEngine *e = GEIST_ENGINE(engine); e->enabled = TRUE;
    if (e->focused && !e->protected_input) pipeline_start(e);
    IBUS_ENGINE_CLASS(geist_engine_parent_class)->enable(engine);
}

static void geist_engine_disable(IBusEngine *engine) {
    GEIST_ENGINE(engine)->enabled = FALSE;
    pipeline_stop(GEIST_ENGINE(engine));
    IBUS_ENGINE_CLASS(geist_engine_parent_class)->disable(engine);
}

static void geist_engine_focus_in(IBusEngine *engine) {
    GeistEngine *e = GEIST_ENGINE(engine);
    e->focused = TRUE;
    if (e->enabled && !e->protected_input) pipeline_start(e);
    if (e->props != NULL) {
        ibus_engine_register_properties(engine, e->props);
    }
    IBUS_ENGINE_CLASS(geist_engine_parent_class)->focus_in(engine);
}

static void geist_engine_focus_out(IBusEngine *engine) {
    GeistEngine *e = GEIST_ENGINE(engine); e->focused = FALSE;
    pipeline_stop(e);
    IBUS_ENGINE_CLASS(geist_engine_parent_class)->focus_out(engine);
}

static void geist_engine_set_content_type(IBusEngine *engine, guint purpose, guint hints) {
    GeistEngine *e = GEIST_ENGINE(engine);
    e->protected_input = purpose == IBUS_INPUT_PURPOSE_PASSWORD || purpose == IBUS_INPUT_PURPOSE_PIN ||
                         (hints & IBUS_INPUT_HINT_PRIVATE);
    if (e->protected_input) pipeline_stop(e);
    else if (e->enabled && e->focused) pipeline_start(e);
}

static void geist_engine_destroy(IBusObject *object) {
    if (g_active_engine == (struct _GeistEngine *) object) {
        g_active_engine = NULL;
    }
    pipeline_stop(GEIST_ENGINE(object));
    g_clear_object(&GEIST_ENGINE(object)->props);
    g_clear_object(&GEIST_ENGINE(object)->state_prop);
    IBUS_OBJECT_CLASS(geist_engine_parent_class)->destroy(object);
}

static void geist_engine_init(GeistEngine *e) {
    g_active_engine = e;
    e->pid        = 0;
    e->watch      = 0;
    e->out        = NULL;
    e->state_prop = ibus_property_new("diktat-state", PROP_TYPE_NORMAL,
                                      ibus_text_new_from_string("diktat"), NULL,
                                      ibus_text_new_from_string("geist-diktat state"), FALSE,
                                      TRUE, PROP_STATE_UNCHECKED, NULL);
    e->props      = ibus_prop_list_new();
    g_object_ref_sink(e->state_prop);
    g_object_ref_sink(e->props);
    ibus_prop_list_append(e->props, e->state_prop);
}

static void geist_engine_class_init(GeistEngineClass *klass) {
    IBusEngineClass *ec         = IBUS_ENGINE_CLASS(klass);
    ec->enable                  = geist_engine_enable;
    ec->disable                 = geist_engine_disable;
    ec->focus_in                = geist_engine_focus_in;
    ec->focus_out               = geist_engine_focus_out;
    ec->set_content_type        = geist_engine_set_content_type;
    IBUS_OBJECT_CLASS(klass)->destroy = geist_engine_destroy;
}

/* ---- main -------------------------------------------------------------- */

static gboolean on_sigterm(gpointer data) {
    (void) data;
    if (g_active_engine != NULL) {
        pipeline_stop(g_active_engine);
    }
    ibus_quit();
    return G_SOURCE_REMOVE;
}

/* Bus gone (session shutdown): same cleanup — a bare ibus_quit would
 * leak the pipeline process group. */
static void on_disconnected(IBusBus *bus, gpointer data) {
    (void) bus;
    (void) data;
    if (g_active_engine != NULL) {
        pipeline_stop(g_active_engine);
    }
    ibus_quit();
}

int main(int argc, char **argv) {
#ifdef GEIST_DIKTAT_TEST_HOOKS
    if (argc > 1 && strcmp(argv[1], "--print-pipeline") == 0) {
        gchar *cmd = pipeline_cmd();
        g_print("%s\n", cmd);
        g_free(cmd);
        return 0;
    }
#endif
    const gboolean from_daemon = argc > 1 && strcmp(argv[1], "--ibus") == 0;

    ibus_init();
    IBusBus *bus = ibus_bus_new();
    if (!ibus_bus_is_connected(bus)) {
        g_printerr("geist-diktat: cannot connect to the ibus daemon\n");
        return 1;
    }
    g_signal_connect(bus, "disconnected", G_CALLBACK(on_disconnected), NULL);

    IBusFactory *factory = ibus_factory_new(ibus_bus_get_connection(bus));
    ibus_factory_add_engine(factory, ENGINE_NAME, GEIST_TYPE_ENGINE);

    if (from_daemon) {
        if (ibus_bus_request_name(bus, BUS_NAME, 0) == 0) {
            g_printerr("geist-diktat: bus name %s is already owned\n", BUS_NAME);
            return 1;
        }
    } else {
        IBusComponent *component = ibus_component_new(
                BUS_NAME, "geist dictation engine", "0.1.0", "Apache-2.0",
                "geisten.net", "https://github.com/geisten/geist-diktat",
                "/usr/libexec/ibus-engine-geist-diktat --ibus", "geist-diktat");
        ibus_component_add_engine(
                component,
                ibus_engine_desc_new(ENGINE_NAME, "geist-diktat (Diktat)",
                                     "local speech-to-text into the focused app", "de",
                                     "Apache-2.0", "geisten.net",
                                     "audio-input-microphone", "default"));
        ibus_bus_register_component(bus, component);
    }

    g_unix_signal_add(SIGTERM, on_sigterm, NULL);
    ibus_main();
    return 0;
}
