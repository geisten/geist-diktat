## Problem und Nachweis

Installation, Modellsetup, Audiogerät, IBus-Eingabequelle und App-Konfiguration sind derzeit mehrere manuelle Schritte. In einer sauberen Ubuntu-Containerumgebung zog das .deb 254 Zusatzpakete; tatsächliche Desktop-Abhängigkeiten sind gesondert zu messen.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P2**. Umsetzungsaufgabe; fehlende Abnahme wird nicht als bereits gemessener Laufzeitfehler ausgegeben.

## Abnahmekriterien

Ein geführter Einstieg prüft Hashes, Speicher/Platz, Capture-Gerät, Berechtigungen, Pfade, IBus/Toolkitmodule und Editorintegration; zeigt Downloadfortschritt, Wiederaufnahme und einen echten kurzen Test mit sichtbarem Transkript. One-Click-Erstinstallation und späteres Ein-Tasten-Diktieren getrennt messen.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
