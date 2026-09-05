## Problem und Nachweis

stdout-Zeilen sind grundsätzlich einfach konsumierbar; Produktionsintegration benötigt verlässliche Framing-/Exit-/Lifecycle-Verträge. Der aktuelle Kern hat EOF- und Fehlerstatusdefekte.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P2**. Umsetzungsaufgabe; fehlende Abnahme wird nicht als bereits gemessener Laufzeitfehler ausgegeben.

## Abnahmekriterien

Versionierte Prozessschnittstelle dokumentieren: PCM-Format, UTF-8/Newline, stdout/stderr-Trennung, Status/Fehler, Cancel, EOF, Zeitstempel optional. Referenzclients Python/C/GLib mit Tests bereitstellen. C-Library-API erst bei belegtem Bedarf; keine Frameworkpflicht.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
