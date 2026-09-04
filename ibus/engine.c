/*
 * ibus-engine-geist-diktat — dictation as an IBus input source.
 *
 * The engine owns the capture lifecycle: selecting the input source
 * (enable) spawns the dictation pipeline; switching away (disable)
 * kills it. Focus changes within the enabled source do NOT stop the
 * mic — you dictate across windows; the privacy boundary is the input
 * source itself. Each transcript line is committed through the standard
 * IME protocol, so every IBus-aware app (GTK, Qt, Electron, VTE
 * terminals) receives it — no uinput, no root.
 *
 * Run modes:
 *   --ibus       spawned by ibus-daemon via the component XML
 *   (standalone) registers its component programmatically — the test
 *                and development mode
 *
 * The pipeline is arecord | /usr/bin/diktat <model>, with the per-user
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
#include <ibus.h>

#include <glib-unix.h>

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
    /* g_get_user_data_dir() is XDG_DATA_HOME with the ~/.local/share
     * fallback; paths are shell-quoted because the string goes to sh -c. */
    gchar *data    = g_build_filename(g_get_user_data_dir(), "geist-diktat", NULL);
    gchar *model   = g_build_filename(data, "gemma4-e2b-Q4_K_M.gguf", NULL);
    gchar *tower   = g_build_filename(data, "audio_tower.safetensors", NULL);
    gchar *q_model = g_shell_quote(model);
    gchar *q_tower = g_shell_quote(tower);
    gchar *cmd     = g_strdup_printf(
            "GEIST_AUDIO_MODEL_PATH=%s "
            "GEIST_MEL_CONSTANTS_PATH=/usr/share/geist-diktat/mel_constants.bin "
            "arecord -q -f S16_LE -r 16000 -c 1 -t raw | "
            "/usr/bin/diktat %s %.0f",
            q_tower, q_model, pipeline_rms());
    g_free(q_tower);
    g_free(q_model);
    g_free(tower);
    g_free(model);
    g_free(data);
    return cmd;
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
static gboolean on_pipeline_line(GIOChannel *ch, GIOCondition cond, gpointer data) {
    GeistEngine *e = data;
    if (cond & G_IO_IN) {
        gchar    *line = NULL;
        gsize     len  = 0;
        GIOStatus st   = g_io_channel_read_line(ch, &line, &len, NULL, NULL);
        if (st == G_IO_STATUS_NORMAL && line != NULL) {
            g_strchomp(line);
            if (line[0] != '\0') {
                gchar *with_space = g_strconcat(line, " ", NULL);
                ibus_engine_commit_text(IBUS_ENGINE(e),
                                        ibus_text_new_from_string(with_space));
                g_free(with_space);
            }
            g_free(line);
            return TRUE;
        }
        g_free(line);
    }
    if (cond & (G_IO_HUP | G_IO_ERR)) {
        e->watch = 0;
        update_state(e, "diktat: pipeline ended");
        return FALSE;
    }
    return TRUE;
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
    e->watch = g_io_add_watch(e->out, G_IO_IN | G_IO_HUP | G_IO_ERR, on_pipeline_line, e);
    update_state(e, "diktat: hört zu");
}

static void pipeline_stop(GeistEngine *e) {
    if (e->pid == 0) {
        return;
    }
    kill(-e->pid, SIGTERM); /* whole process group */
    g_spawn_close_pid(e->pid);
    e->pid = 0;
    if (e->watch != 0) {
        g_source_remove(e->watch);
        e->watch = 0;
    }
    if (e->out != NULL) {
        g_io_channel_unref(e->out);
        e->out = NULL;
    }
    update_state(e, "diktat: aus");
}

/* ---- IBusEngine vfuncs ------------------------------------------------ */

static void geist_engine_enable(IBusEngine *engine) {
    pipeline_start(GEIST_ENGINE(engine));
    IBUS_ENGINE_CLASS(geist_engine_parent_class)->enable(engine);
}

static void geist_engine_disable(IBusEngine *engine) {
    pipeline_stop(GEIST_ENGINE(engine));
    IBUS_ENGINE_CLASS(geist_engine_parent_class)->disable(engine);
}

static void geist_engine_focus_in(IBusEngine *engine) {
    GeistEngine *e = GEIST_ENGINE(engine);
    if (e->props != NULL) {
        ibus_engine_register_properties(engine, e->props);
    }
    IBUS_ENGINE_CLASS(geist_engine_parent_class)->focus_in(engine);
}

static void geist_engine_destroy(IBusObject *object) {
    if (g_active_engine == (struct _GeistEngine *) object) {
        g_active_engine = NULL;
    }
    pipeline_stop(GEIST_ENGINE(object));
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
