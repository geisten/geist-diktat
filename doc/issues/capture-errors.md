## Problem und Nachweis

Launcher.test_capture_error_is_not_success zeigt: Capture scheitert, Decoder endet normal, POSIX-Pipeline liefert 0. Damit kann eine nicht funktionierende Aufnahme als erfolgreich erscheinen.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P1**. Reproduzierbarer Defekt.

[Betroffener Quelltext](https://github.com/geisten/geist-diktat/blob/607d19446f8b6e833dced56446bc44410c24ca9d/packaging/geist-diktat).

[Reproduktion / Regressionstest](https://github.com/geisten/geist-diktat/blob/457ab69/tests/test_launcher.py).

## Abnahmekriterien

Capture und Decoder als verwaltete Prozesse mit beiden Exitstatus führen. Fehlender Recorder, Gerät belegt, Trennung und Decoderabbruch ergeben sichtbaren Fehler; Stop hinterlässt keine Prozesse.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
