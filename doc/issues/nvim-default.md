## Problem und Nachweis

Codebefund: Standardcmd verwendet auch auf macOS arecord, Binary-Pfad ist ungequotet; Tower-/Mel-Pfade des Launchers fehlen. Funktionierender Audit-Workaround: setup({cmd="geist-diktat run"}).

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P2**. Reproduzierbarer Defekt.

[Betroffener Quelltext](https://github.com/geisten/geist-diktat/blob/607d19446f8b6e833dced56446bc44410c24ca9d/lua/geist-diktat/init.lua).

## Abnahmekriterien

Frische Installation unter macOS und Ubuntu aus beliebigem cwd ohne Pfadkonfiguration starten. Leerzeichen im Installationspfad, XDG_DATA_HOME und Capture-Auswahl testen; :checkhealth meldet konkrete Reparaturschritte.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
