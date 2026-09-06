## Problem und Nachweis

Core.test_unicode_boundary_sanitized: 4094 ASCII-Bytes plus ü werden am Ausgabelimit in der Mitte des Codepoints abgeschnitten; stdout ist ungültiges UTF-8.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P2**. Reproduzierbarer Defekt.

[Betroffener Quelltext](https://github.com/geisten/geist-diktat/blob/607d19446f8b6e833dced56446bc44410c24ca9d/src/diktat.c).

[Reproduktion / Regressionstest](https://github.com/geisten/geist-diktat/blob/457ab69/tests/test_core.py).

## Abnahmekriterien

Nur vollständige Codepoints übernehmen, Trunkierung diagnostizieren. Grenztests für 2/3/4-Byte-Codepoints und mehrere Tokenstücke, unter ASan/UBSan.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
