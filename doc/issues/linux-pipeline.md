## Problem und Nachweis

Das dokumentierte `| wtype -` garantiert keine sofortige Ausgabe jeder kurzen Transkriptzeile: upstream wtype puffert stdin in 100-Zeichen-Blöcken bis EOF/Blockende. Ein kurzer laufender Stream kann deshalb ohne sichtbaren Text bleiben. Quelle: https://github.com/atx/wtype/blob/master/main.c

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P2**. Umsetzungsaufgabe; fehlende Abnahme wird nicht als bereits gemessener Laufzeitfehler ausgegeben.

[Betroffener Quelltext](https://github.com/geisten/geist-diktat/blob/607d19446f8b6e833dced56446bc44410c24ca9d/README.md).

## Abnahmekriterien

Zeilenweisen Adapter oder IBus empfehlen und jedes dokumentierte Beispiel mit echter zeitlich fragmentierter Ausgabe prüfen. Wayland-Protokollunterstützung und Compositorgrenzen dokumentieren. Stop darf keinen Text nachschieben.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
