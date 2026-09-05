## Problem und Nachweis

Kontrollierte on_exit/on_stdout-Callbacks zeigen: alter Exit löscht ID einer neuen Sitzung; bereits geplante Ausgabe kann nach Stop eingefügt werden.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P1**. Reproduzierbarer Defekt.

[Betroffener Quelltext](https://github.com/geisten/geist-diktat/blob/607d19446f8b6e833dced56446bc44410c24ca9d/lua/geist-diktat/init.lua).

[Reproduktion / Regressionstest](https://github.com/geisten/geist-diktat/blob/457ab69/tests/nvim_contract.lua).

## Abnahmekriterien

Sitzungsgeneration in allen Callbacks einschließlich vim.schedule validieren. Stop invalidiert Generation vor jobstop. 100 schnelle Toggle-Zyklen dürfen weder Text noch Status einer anderen Sitzung verändern.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
