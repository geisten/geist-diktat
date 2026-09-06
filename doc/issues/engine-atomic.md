## Problem und Nachweis

EngineSync.test_gitfile_checkout_survives_failed_clone zeigt Datenverlust: `.git` als Datei wird nicht erkannt, rm -rf löscht den Checkout einschließlich lokaler Modelldatei, nachfolgender Clone scheitert.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P1**. Reproduzierbarer Defekt.

[Betroffener Quelltext](https://github.com/geisten/geist-diktat/blob/607d19446f8b6e833dced56446bc44410c24ca9d/scripts/sync-engine.sh).

[Reproduktion / Regressionstest](https://github.com/geisten/geist-diktat/blob/457ab69/tests/test_engine_sync.py).

## Abnahmekriterien

Checkouts über git rev-parse erkennen. Nie vorhandene Daten vor erfolgreich vorbereitetem Ersatz löschen. Tests für Submodule, Worktrees, kaputte Git-Metadaten und Offline-Migration. Modelldaten getrennt halten.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
