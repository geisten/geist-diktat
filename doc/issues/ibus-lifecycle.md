## Problem und Nachweis

12 Lifecycle-Prüfungen, zwei Fehler: G_SPAWN_DO_NOT_REAP_CHILD ohne Child-Watch/waitpid hinterlässt ein nicht eingesammeltes Kind; e->pid bleibt nach natürlichem EOF gesetzt und blockiert Neustart.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P2**. Reproduzierbarer Defekt.

[Betroffener Quelltext](https://github.com/geisten/geist-diktat/blob/607d19446f8b6e833dced56446bc44410c24ca9d/ibus/engine.c).

[Reproduktion / Regressionstest](https://github.com/geisten/geist-diktat/blob/457ab69/tests/ibus_lifecycle.c).

## Abnahmekriterien

Child-Watch einrichten, Exit-/Stop-Aufräumen idempotent machen, PID/IO-Watches zurücksetzen. 100 Enable/Disable/EOF/Focus-Zyklen ohne Zombies oder blockierten Neustart bestehen.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
