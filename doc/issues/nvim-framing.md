## Problem und Nachweis

Realer Producer `printf hel; sleep 0.15; printf "lo\n"` wird als `hel lo ` statt `hello ` eingefügt. Kontrollierte Lua-Tests decken zusätzlich aufgeteilte UTF-8-Bytes ab.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P1**. Reproduzierbarer Defekt.

[Betroffener Quelltext](https://github.com/geisten/geist-diktat/blob/607d19446f8b6e833dced56446bc44410c24ca9d/lua/geist-diktat/init.lua).

[Reproduktion / Regressionstest](https://github.com/geisten/geist-diktat/blob/457ab69/tests/test_editors.py).

## Abnahmekriterien

Je Job einen Byte-/Zeilenpuffer führen, ausschließlich vollständige Zeilen einfügen, EOF-Rest explizit behandeln. Alle Splitpunkte von Umlauten/Emoji und mehrere Zeilen pro Callback testen.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
