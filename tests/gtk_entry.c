#include <gtk/gtk.h>
#include <stdio.h>
static void changed(GtkEditable *editable, gpointer unused) {
    (void)unused;
    const char *s=gtk_entry_get_text(GTK_ENTRY(editable));
    if (*s) { puts(s); fflush(stdout); gtk_main_quit(); }
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
