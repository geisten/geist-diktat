## Problem und Nachweis

Core.test_eof_flushes_speech und Core.test_partial_final_frame_preserved schlagen fehl. Ein PCM-Stream mit 25 Sprachframes ohne angehängte Stille endet ohne Transkript; ein letzter Teilframe wird nicht verarbeitet.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P1**. Reproduzierbarer Defekt.

[Betroffener Quelltext](https://github.com/geisten/geist-diktat/blob/607d19446f8b6e833dced56446bc44410c24ca9d/src/diktat.c).

[Reproduktion / Regressionstest](https://github.com/geisten/geist-diktat/blob/457ab69/tests/test_core.py).

## Abnahmekriterien

EOF muss gültige laufende Sprache genau einmal abschließen, einen geraden PCM16-Teilframe erhalten und kurze Geräusche weiterhin verwerfen. Leere Eingabe, mehrfaches EOF und Decoderfehler prüfen.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
