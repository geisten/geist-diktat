## Problem und Nachweis

Kern decodiert synchron zwischen Aufnahmeabschnitten. Auf Pi5 war Durchsatz im Audit langsamer als Echtzeit; Pipe-Backpressure ist bei langen Streams ein konkretes Architekturproblem. Hardware-Mikrofonverluste sind bisher nicht direkt gemessen.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P2**. Umsetzungsaufgabe; fehlende Abnahme wird nicht als bereits gemessener Laufzeitfehler ausgegeben.

## Abnahmekriterien

Capture unabhängig weiterführen, begrenzten Ringpuffer und sichtbare Überlaufpolitik definieren. Residenten Modellprozess mit Idle-/Speicherpolitik prüfen, um erneutes Laden beim Toggle zu vermeiden. 30/60-min-Tests: kein stiller Frameverlust, Speicherplateau, definierter Cancel/Überlastzustand.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).

## Neuer End-to-End-Nachweis auf Pi5

Das echte OOCC-Gespräch (Paar 1, freie Unterhaltung, https://doi.org/10.5281/zenodo.21446419) wurde identisch auf Mac/Pi als PCM16/16k mono mit 20-ms-Takt angeboten: 616,815 s Audio. Pi5, 4 GiB, vier OpenMP-Threads, unveränderte Produktion:

- 939,978 s Gesamtzeit, WER 40,2 % (593/1475), Exit 0, 60 Ausgabezeilen.
- Letzte Ausgabe 321,47 s nach dem nominellen Audioende.
- Python-Zuspieler am Ende um 294,76 s zurück: belegte Pipe-Backpressure, keine Behauptung direkt gemessener ALSA-Frameverluste.
- Peak RSS 2866,6 MiB; während des Laufs etwa 1106 MiB systemweiter Swap belegt, punktuell 77,1 °C. Das sind keine kontinuierlichen Prozess-Swap-/Temperaturmessungen.

Mac-Kontrolle: 622,894 s Gesamtzeit, WER 30,4 %, letzte Ausgabe 4,93 s nach Audioende, kein abschließender Zuspielrückstand.

Die Warteschlange allein beschleunigt das Modell nicht. Ein täglicher Live-Aufnahmepfad braucht Durchsatzreserve, begrenzte Puffer und einen erkennbaren Überlastzustand; 10 Minuten Diktat dürfen nicht unbemerkt über fünf Minuten nachlaufen.
