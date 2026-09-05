## Problem und Nachweis

Nachgewiesen: echte GTK3-/Qt5-Eingabefelder über private IBus-Sitzung unter Xvfb funktionieren, auch mit echtem Modell. Nicht nachgewiesen: Live-GNOME-Wayland/KDE, GTK4, Electron/Browser, LibreOffice, Flatpak/Snap.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P2**. Umsetzungsaufgabe; fehlende Abnahme wird nicht als bereits gemessener Laufzeitfehler ausgegeben.

## Abnahmekriterien

Desktop-Matrix mit GNOME Wayland/Xorg, KDE, GTK3/4, Qt5/6, Firefox/Chromium, Electron, LibreOffice, Terminal und Flatpak/Snap. Eingabequelle, Shortcut, Fokus, Passwortfelder, Prozessende, Unicode und Wiederaufnahme prüfen. Fehlende Unterstützung klar anzeigen; keine globale Session ungefragt neu starten.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
