## Problem und Nachweis

Queue wird erst durch das nächste Transkript geleert, bleibt nach Stop erhalten und kann in neue Sitzung gelangen. pcall verschluckt Fehler nicht modifizierbarer Buffer.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P2**. Reproduzierbarer Defekt.

[Betroffener Quelltext](https://github.com/geisten/geist-diktat/blob/607d19446f8b6e833dced56446bc44410c24ca9d/lua/geist-diktat/init.lua).

[Reproduktion / Regressionstest](https://github.com/geisten/geist-diktat/blob/457ab69/tests/nvim_contract.lua).

## Abnahmekriterien

ModeChanged oder äquivalenter sicherer Hook leert Queue genau einmal; Stop verwirft alte Queue sichtbar. BufDelete/nonmodifiable/ungültiges Fenster dürfen keinen stillen Textverlust verursachen; Zielbufferpolitik dokumentieren.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
