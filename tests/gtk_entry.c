#define _POSIX_C_SOURCE 200809L
#include <gtk/gtk.h>
#include "../src/trace.h"
#include <stdio.h>
static gboolean finish(gpointer unused) { (void)unused; gtk_main_quit(); return G_SOURCE_REMOVE; }
static void changed(GtkEditable *editable, gpointer unused) {
    (void)unused;
    const char *s=gtk_entry_get_text(GTK_ENTRY(editable));
    if (*s) { diktat_trace("gtk", "app_observed", 0, 1, 0); puts(s); fflush(stdout); g_timeout_add(200,finish,NULL); }
}
int main(int argc,char **argv) {
    gtk_init(&argc,&argv);
    GtkWidget *window=gtk_window_new(GTK_WINDOW_TOPLEVEL);
    gtk_window_set_title(GTK_WINDOW(window),"GeistAuditGTK");
    GtkWidget *entry=gtk_entry_new();
    gtk_container_add(GTK_CONTAINER(window),entry);
    g_signal_connect(entry,"changed",G_CALLBACK(changed),NULL);
    gtk_widget_show_all(window);
    gtk_widget_grab_focus(entry);
    gtk_window_present(GTK_WINDOW(window));
    gtk_main();
    return 0;
}
