## Problem und Nachweis

Core.test_stream_errors_propagate injiziert reset/begin/push/poll/end/prefill/decode-Fehler. Der Prozess meldet bei diesen Laufzeitfehlern Erfolg (Exit 0).

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P1**. Reproduzierbarer Defekt.

[Betroffener Quelltext](https://github.com/geisten/geist-diktat/blob/607d19446f8b6e833dced56446bc44410c24ca9d/src/diktat.c).

[Reproduktion / Regressionstest](https://github.com/geisten/geist-diktat/blob/457ab69/tests/test_core.py).

## Abnahmekriterien

Jeder fatale Enginefehler erzeugt einen dokumentierten Nichtnull-Exitcode und stderr-Diagnose; Ressourcen werden genau einmal freigegeben. Kein Teiltranskript als erfolgreicher Abschluss.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
