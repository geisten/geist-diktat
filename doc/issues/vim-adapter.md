## Problem und Nachweis

Nachgewiesen ist nur endliches `:read !...` mit Unicode. Ein unendlicher Diktierprozess blockiert diesen Weg; IBus-Eingaben in einem Terminal im Normalmodus können als Vim-Kommandos wirken. Kein nativer Vim-Adapter vorhanden.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P2**. Umsetzungsaufgabe; fehlende Abnahme wird nicht als bereits gemessener Laufzeitfehler ausgegeben.

## Abnahmekriterien

Vim job_start/channel-basierter Adapter: Start/Stop/Toggle, zeilenweise UTF-8-Pufferung, generation-sichere Callbacks, definierte Normal/Insert/Commandline-Politik, Undo-Gruppierung und Fokuswechsel. Tests mit echtem Vim, nicht einer nvim-Symlink-Installation.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
