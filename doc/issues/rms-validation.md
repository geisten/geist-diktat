## Problem und Nachweis

Core.test_invalid_threshold_rejected weist akzeptierte Werte abc/nan/inf/-1/0/300junk nach. atof verschluckt Parsingfehler.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P2**. Reproduzierbarer Defekt.

[Betroffener Quelltext](https://github.com/geisten/geist-diktat/blob/607d19446f8b6e833dced56446bc44410c24ca9d/src/diktat.c).

[Reproduktion / Regressionstest](https://github.com/geisten/geist-diktat/blob/457ab69/tests/test_core.py).

## Abnahmekriterien

strtof/strtod mit endptr/errno und finite/range-Prüfung verwenden. Ungültige Werte liefern Usage-Status 2, ohne Modell zu laden; dokumentierter gültiger Bereich.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
