#include <QApplication>
#include <QLineEdit>
#include <cstdio>
int main(int argc,char **argv) {
    QApplication app(argc,argv);
    QLineEdit entry;
    entry.setWindowTitle("GeistAuditQt");
    QObject::connect(&entry,&QLineEdit::textChanged,[&](const QString &s) {
        if (!s.isEmpty()) { std::puts(s.toUtf8().constData()); std::fflush(stdout); app.quit(); }
    });
    entry.show(); entry.activateWindow(); entry.setFocus();
    return app.exec();
}
