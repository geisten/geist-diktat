## Problem und Nachweis

Neue Pilotmessung nutzt FLEURS-de, acht SwissDial-Varianten, kontrolliertes Rauschen und ein echtes OOCC-Gespräch. Ein englischer Clip mit 0 % WER belegt keine deutsche Alltagsqualität. Für Betthupferl-Audio ist individuelle Freigabe erforderlich.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P2**. Umsetzungsaufgabe; fehlende Abnahme wird nicht als bereits gemessener Laufzeitfehler ausgegeben.

[Reproduktion / Regressionstest](https://github.com/geisten/geist-diktat/blob/457ab69/tests/test_quality.py).

## Abnahmekriterien

Menschenaufnahmen aus Deutschland/Österreich/Schweiz und Alltagssituationen mit erlaubter Nutzung und unabhängigen Referenzen beschaffen. Getrennte WER nach Dialekt/Standardisierung/SNR, S/I/D, Wortgewichtung und Konfidenzintervalle; keine synthetische Sprache als menschlich ausgeben. Gesicherte Regressionen auf macOS/Pi5/Ubuntu; Grenzen und Lizenzen dokumentieren.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
