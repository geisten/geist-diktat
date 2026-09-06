#include "../src/trace.h"
#include <QApplication>
#include <QLineEdit>
#include <QTimer>
#include <cstdio>
int main(int argc,char **argv) {
    QApplication app(argc,argv);
    QLineEdit entry;
    entry.setWindowTitle("GeistAuditQt");
    QObject::connect(&entry,&QLineEdit::textChanged,[&](const QString &s) {
        if (!s.isEmpty()) { diktat_trace("qt", "app_observed", 0, 1, 0); std::puts(s.toUtf8().constData()); std::fflush(stdout); QTimer::singleShot(200,&app,&QApplication::quit); }
    });
    entry.show(); entry.activateWindow(); entry.setFocus();
    return app.exec();
}
