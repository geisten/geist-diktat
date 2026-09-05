/* Real IBusEngine object on a private test bus; no physical microphone. */
#define main engine_main
#define GEIST_DIKTAT_TEST_HOOKS
#include "../ibus/engine.c"
#undef main
#include <assert.h>
int main(void) {
    ibus_init();
    IBusBus *bus=ibus_bus_new();
    assert(ibus_bus_is_connected(bus));
    IBusEngine *base=ibus_engine_new_with_type(GEIST_TYPE_ENGINE, "geist-privacy-test",
        "/org/freedesktop/IBus/Engine/PrivacyTest",ibus_bus_get_connection(bus));
    assert(base); g_object_ref_sink(base);
    GeistEngine *e=GEIST_ENGINE(base);
    g_setenv("GEIST_DIKTAT_CMD","sleep 30",TRUE);
    e->enabled=TRUE;e->focused=TRUE;
    geist_engine_set_content_type(base,IBUS_INPUT_PURPOSE_PASSWORD,0);assert(e->pid==0);
    geist_engine_set_content_type(base,IBUS_INPUT_PURPOSE_PIN,0);assert(e->pid==0);
    geist_engine_set_content_type(base,IBUS_INPUT_PURPOSE_FREE_FORM,IBUS_INPUT_HINT_PRIVATE);assert(e->pid==0);
    geist_engine_set_content_type(base,IBUS_INPUT_PURPOSE_FREE_FORM,0);assert(e->pid>0);
    geist_engine_set_content_type(base,IBUS_INPUT_PURPOSE_PASSWORD,0);assert(e->pid==0);
    geist_engine_set_content_type(base,IBUS_INPUT_PURPOSE_FREE_FORM,0);assert(e->pid>0);
    geist_engine_focus_out(base);assert(e->pid==0 && !e->focused);
    geist_engine_focus_in(base);assert(e->pid>0);
    geist_engine_disable(base);assert(e->pid==0 && !e->enabled);
    geist_engine_focus_in(base);assert(e->pid==0);
    ibus_object_destroy(IBUS_OBJECT(base));g_object_unref(base);g_object_unref(bus);
    puts("PASS password/PIN/private fields, focus loss, restart and disable");
    return 0;
}
