# Supervisor und Modellhaltung auf dem Pi5

Implementierung zu #36/#37, September 2026. Der Pi5 bleibt ein experimentelles
Profil. Der lokale Worker ergänzt den bisherigen begrenzten Supervisor und den
residenten Whisper-Decoder; er ist kein Netzwerkdienst und kein öffentlich
zugesagtes Ereignisprotokoll.

## Verhalten beim Diktieren

Das installierte `whisper-small`-Profil verwendet standardmäßig den Modellworker
mit vier Threads und `OMP_WAIT_POLICY=PASSIVE`. Eine ausdrückliche Thread-/Wait-
Konfiguration bleibt möglich. Capture startet erst, wenn der Worker ein geladenes
Modell und eine zugeordnete Sitzung bestätigt. Kaltes Laden verbraucht somit nicht
den sechsekündigen Aufnahme-Puffer.

```sh
geist-diktat worker start   # optional vorladen, ohne Mikrofonaufnahme
geist-diktat worker status  # Modell/PID, belegt/frei, Leerlaufgrenze
geist-diktat run            # Aufnahme und normale UTF-8-Textzeilen
geist-diktat worker stop    # Modell und gegebenenfalls Sitzung beenden
```

Ein reguläres Audioende finalisiert den letzten Abschnitt und erhält das Modell.
Stop während des Wartens auf neue Sprache verwirft die unvollständige Sitzung;
VAD, Audio und Ausgaben werden für die nächste Sitzung zurückgesetzt. Jede Sitzung
hat eine neue Kennung. Stop während Decode verwirft den Modellprozess, weil die
Engine einen Abbruch nicht in jeder Rechenphase zeitnah quittiert. Der nächste
Start lädt dann neu. Ein außerhalb des Decodes angeforderter Sitzungsabbruch
bekommt höchstens 350 ms zur Quittierung, danach wird ebenfalls neu geladen.

Nach standardmäßig **60 Sekunden ohne aktive Sitzung** endet der Dienst und gibt
Modell sowie Speicher frei. `GEIST_DIKTAT_IDLE_SECONDS` erlaubt 1–3600 Sekunden.
`GEIST_DIKTAT_REUSE_MODEL=0` wählt ausdrücklich den bisherigen Prozess je Diktat.
Doctor berichtet die konfigurierte Workerpolitik. Status und Stop funktionieren
auch bei beschädigter Profilkonfiguration. Bei geändertem Modell/Binary oder
anderen Decoderparametern den bestehenden Worker mit `worker stop` beenden;
ein abweichender Client erhält einen Fehler statt eine falsche Konfiguration.

## Grenzen und Schutz gegen Rückstand

- Aufnahmequeue: weiterhin sechs Sekunden standardmäßig, sichtbarer Überlauf
  mit Exit 75. Capture und Decoderclient gehören der aufrufenden Sitzung.
- Transport zum Modell: höchstens eine Sekunde gepufferte PCM-Pakete plus eine
  Sekunde Lookahead im C++-Leser. Betriebssystem-Pipes/Sockets kommen hinzu.
- Ausgabe: begrenzte Ereignis-/Textpuffer; keine unbegrenzte Sitzungsliste.
  Ein weiterer aktiver Start erhält Busy (Exit 73).
- Der private Unix-Socket liegt unter `$XDG_RUNTIME_DIR/geist-diktat`, ersatzweise
  `$XDG_CACHE_HOME/geist-diktat` bzw. `~/.cache/geist-diktat`. Das Verzeichnis muss
  dem Benutzer gehören, Modus 0700 haben und darf kein Symlink sein. Der Socket
  hat Modus 0600; ein Betriebssystem-Lock verhindert doppelte Dienste.
- Modellpfad, Dateistand, Decoder, RMS und wirksame Parameter müssen zum laufenden
  Dienst passen. Alte Sitzungen liefern keinen Text in die neue Sitzung.
- Keine Speicherung von aufgenommenem PCM oder Transkript durch den Worker.
  Optionaler Trace enthält numerische Zustands-/Audiozähler. Die neuen
  `buffer_state`-Proben dokumentieren den Rückstand alle fünf Sekunden.

Der Worker beschleunigt eine laufende Inferenz nicht beliebig. Ein ausreichend
schneller Decoder, geprüfte Sprachqualität und brauchbare Endlatenz bleiben nötig.
Insbesondere ist ein RTF unter 1 noch kein Nachweis von höchstens drei Sekunden
bis zur Einfügung.

## Reproduzierbare Messungen

`benchmarks/worker_bench.py` prüft identische menschliche deutsche Aufnahmen mit
frei gewählter Thread-/Beam-/Wait-Matrix. Modellladen wird separat gemessen; die
folgenden Aufrufe nutzen denselben Modellprozess. WER, Bytevollständigkeit,
Laufzeit, PID, Prozessbaum-RSS/-Swap, systemweiter Swap, Temperatur und
`get_throttled` werden getrennt erfasst. Vorhandene historische Drosselungsbits
sind keine während dieses Laufs beobachtete Drosselung.

```sh
python3 benchmarks/worker_bench.py --binary build/whisper-resident/diktat-whisper \
  --model build/ggml-small-q5_1.bin --manifest build/speech-corpus/manifest.json \
  --threads 1,2,4 --beams 5 --waits PASSIVE,ACTIVE --per-group 1 \
  --output build/pi-worker-screening.json
# Vollständiger Entwicklungs-Pilot statt Vorauswahl:
python3 benchmarks/worker_bench.py --binary build/whisper-resident/diktat-whisper \
  --model build/ggml-small-q5_1.bin --manifest build/speech-corpus/manifest.json \
  --threads 4 --beams 5 --per-group 0 --output build/pi-worker-quality.json
```

`--paced` prüft zeitgetreue Zuführung. Die dabei ausgewiesene Latenz bezieht sich
auf das Dateiende, nicht auf menschlich annotierte Sprachendpunkte oder eine
Zielfeldänderung. Sehr kleine Stichproben tragen ihren Umfang bei p50/p95 mit.

`benchmarks/worker_soak.py` führt den tatsächlichen Supervisor mit Workerclient
und einer zeitgetreuen Dateiquelle aus. Für einen Stundenlauf wird vorhandene
Gesprächssprache wiederholt. Referenzen und Audio bleiben lokal; nur numerische
Metriken und Hashes werden archiviert. Ein 60-Minuten-Lauf enthält einen
30-Minuten-Zwischenstand und ist kein zusätzlich separat abgeschlossener
30-Minuten-Lauf.

```sh
python3 benchmarks/worker_soak.py --binary build/whisper-resident/diktat-whisper \
  --model build/ggml-small-q5_1.bin --manifest build/speech-corpus/manifest.json \
  --group de-conversation-long --minutes 60 --threads 4 --beam 5 \
  --output build/pi-worker-soak.json
```

Nur vollständige Läufe bekommen eine WER. Für lange Läufe müssen Byte-/Sample-
Bilanz, ein Modellladen, Speichergrenze (1,5 GiB Prozessbaum), höchstens 64 MiB
Anstieg der RSS-Mediane nach Aufwärmen, kein Prozess-Swap und keine beobachteten
aktiven Drosselungsbits bestehen. Hardwaremodell, Betriebssystem und tatsächlich
vorhandene Konkurrenzlast gehören zur Auswertung. Diese Tests ersetzen weder
physische Mikrofon-/Treiberabnahme noch das Einfügen in reale Anwendungen.
