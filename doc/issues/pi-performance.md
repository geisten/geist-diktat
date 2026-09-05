## Problem und Nachweis

Vorheriger gepinnter 9,06-s-Test: Pi5 Durchsatz-RTF 1,884, Endlatenz bei Echtzeitzuspielung 8,589 s; 4-GiB-Gerät verwendet Swap. Wichtige Präzisierung nach Verfolgung des API-Aufrufpfads: Der Encoder-Konstruktor startet den Worker nur bei GEIST_AUDIO_STREAM=1 vorab. Der von diktat verwendete geist_session_audio_begin-Pfad startet denselben Worker jedoch ohnehin in audio_conformer_stream_begin (arch.c). GEIST_AUDIO_STREAM=0/1 ist für dieses Produkt daher KEIN Streaming-Aus/An-Vergleich, sondern höchstens ein Vergleich des Startzeitpunkts.

Geprüfter Produktstand: `607d19446f8b6e833dced56446bc44410c24ca9d` (relevante Dateien identisch zum lokalen Audit). Priorität **P2**. Umsetzungsaufgabe; fehlende Abnahme wird nicht als bereits gemessener Laufzeitfehler ausgegeben.

## Abnahmekriterien

A/B mit Threads 1/2/4, OMP_WAIT_POLICY und GEIST_AUDIO_SUBSAMPLE_INC=0/1; GEIST_AUDIO_STREAM=0/1 nur als Kontrolle des frühen/lazy Workerstarts, nicht als vermeintliche Streaming-Aktivierung; identische Modelldateien/Fixtures, WER plus p50/p95-Endlatenz, RTF, RSS/Swap, Temperaturen und Drosselungsflags messen. Qualität darf nicht zugunsten Geschwindigkeit verschwiegen werden. Gewinner anschließend auf langen echten Gesprächen testen.

## Validierung

Betroffene Plattformen getrennt prüfen; fehlschlagende Regressionen müssen nach dem Fix grün werden. Rohprotokolle und verwendeten Commit angeben. [Ubuntu x64/ARM64 Auditlauf](https://github.com/geisten/geist-diktat/actions/runs/33969978051).
