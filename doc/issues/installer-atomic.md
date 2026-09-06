## Problem und Nachweis

Installer.test_extraction_failure_preserves_previous_install schlägt fehl. DEST wird vor erfolgreichem Entpacken gelöscht; simulierter tar-Fehler entfernt die funktionierende Vorversion.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P1**. Reproduzierbarer Defekt.

[Betroffener Quelltext](https://github.com/geisten/geist-diktat/blob/607d19446f8b6e833dced56446bc44410c24ca9d/install.sh).

[Reproduktion / Regressionstest](https://github.com/geisten/geist-diktat/blob/457ab69/tests/test_installer.py).

## Abnahmekriterien

In separates Verzeichnis laden/prüfen/entpacken, ausführbare Artefakte prüfen, erst danach atomar wechseln. Bei Netzwerk-/Hash-/tar-/Platzfehlern bleibt alte Version ausführbar. Abbruch und Rollback testen.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
