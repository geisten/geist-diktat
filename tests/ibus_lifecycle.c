/* No system registry, desktop session or microphone needed. */
#define main engine_main
#define GEIST_DIKTAT_TEST_HOOKS
#include "../ibus/engine.c"
#undef main
#include <errno.h>
#include <sys/wait.h>
#include <time.h>

static int failures;
static void result(const char *name, gboolean ok) {
    printf("%s %s\n",ok ? "PASS" : "FAIL",name);
    failures += !ok;
}
int main(void) {
    const char *bad[]={"300; false", "nan", "inf", "-1", "0", "300x"};
    for (size_t i=0;i<G_N_ELEMENTS(bad);i++) {
        g_setenv("GEIST_DIKTAT_RMS",bad[i],TRUE);
        result(bad[i],pipeline_rms()==300.0);
    }
    g_setenv("GEIST_DIKTAT_RMS","420",TRUE);
    result("numeric RMS",pipeline_rms()==420.0);
    g_setenv("GEIST_DIKTAT_CMD","sleep 30",TRUE);
    GeistEngine e={0};
    pipeline_start(&e);
    GPid pid=e.pid;
    result("pipeline spawned",pid>0);
    pipeline_start(&e);
    result("duplicate start ignored",e.pid==pid);
    /* Allow child setup to establish its process group before stop. */
    g_usleep(100000);
    pipeline_stop(&e);
    result("stop clears resources",e.pid==0 && e.out==NULL && e.watch==0);
    g_usleep(100000);
    int status=0;
    pid_t child=waitpid(pid,&status,WNOHANG);
    result("stopped child already reaped",child==-1 && errno==ECHILD);
    if (child==0) { kill(pid,SIGKILL); waitpid(pid,&status,0); }
    g_setenv("GEIST_DIKTAT_CMD","exit 0",TRUE);
    pipeline_start(&e);
    pid=e.pid;
    for (int i=0;i<20;i++) {
        while (g_main_context_iteration(NULL,FALSE)) {}
        g_usleep(10000);
    }
    result("natural exit clears pid for restart",e.pid==0);
    pipeline_stop(&e);
    waitpid(pid,&status,0);
    return failures ? 1 : 0;
}
