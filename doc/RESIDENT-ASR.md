# Residenter Whisper-Kandidat für Ubuntu

Der experimentelle `diktat-whisper`-Prozess nutzt die öffentliche whisper.cpp-API
auf Revision `52a939a2a762224e255d366c1182b2af4dd1a032`. Er lädt Modell und Kontext
**einmal je Sitzung**. Der bisherige Vergleichsadapter
`benchmarks/whisper_stream.py` bleibt zur historischen Reproduktion erhalten und
startet weiterhin ein eigenes CLI pro VAD-Segment. Der ausgelieferte Standard
bleibt Geist, bis Auswahl und Produktabnahme abgeschlossen sind.

## Aufbau und Grenzen

- Rohes Mono-PCM16LE mit 16 kHz kommt über stdin; finale UTF-8-Textzeilen gehen
  über stdout. Status und Modellmeldungen gehen ausschließlich über stderr.
- Die vorhandene RMS-Segmentierung bleibt vergleichbar: 20-ms-Frames, Öffnen nach
  drei lauten Frames, Schließen nach 40 leisen Frames, maximal 28 s pro Fenster.
  Auch ein vollständiges PCM-Sample im letzten Teilframe bleibt erhalten.
- Ein eigener Leser nimmt während des Decodes bis zu **einer Sekunde** Audio
  voraus. Danach wirkt Rückstau in die Pipe. Der vorhandene externe Supervisor
  behält seine sechs Sekunden Queue und den expliziten Überlastabbruch; es gibt
  weder unbegrenzte Puffer noch stilles Verwerfen von Frames.
- Ein Kontext bearbeitet alle Segmente sequenziell. `no_context=true` verhindert
  die Übernahme alter Transkripte als Prompt zwischen Aufrufen. Innerhalb eines
  Whisper-Aufrufs gelten die internen Decodermechanismen weiterhin.
- CPU-Ausführung, Sprache `de`, keine Übersetzung, keine automatischen partiellen
  Einfügungen. Beam 1 und 5 werden getrennt gemessen. Die standardmäßige
  Temperatur-Fallbackstrategie bleibt erhalten; deterministische Textgleichheit
  über Plattformen wird nicht versprochen.
- Audiofenster sind auf 28 s begrenzt. Überlange Ausgabe wird vor der Einfügung
  als Fehler zurückgewiesen. Speicher des eigentlichen Modells/Decoders kommt
  zusätzlich zu diesen Audiopuffern hinzu.

Die zusätzliche Sekunde Lesepuffer ist keine Lösung für einen dauerhaft zu
langsamen Decoder. Eine gemessene, vollständige Sitzung belegt keinen beliebig
langen Dauerbetrieb. Kürzere Fenster, Überlappungen, ein besseres VAD und eine
Decoder-Auswahl bleiben getrennte Experimente mit eigenen Qualitätsprüfungen.

## Bauen und kontrolliert ausführen

Benötigt werden Git, CMake, Python 3 und ein C++17-Compiler. Der Build ist ein
Entwicklerpfad, noch kein geführtes Produktsetup. Das Skript erhält bestehende
Checkouts und baut den Kandidaten getrennt vom normalen `make`-Ergebnis.

```sh
sh scripts/build-whisper.sh
python3 scripts/fetch-whisper-model.py
OMP_NUM_THREADS=4 GEIST_WHISPER_BEAM_SIZE=1 \
  build/whisper-resident/diktat-whisper build/ggml-small-q5_1.bin < recording.pcm
```

Der Modell-Download prüft SHA-256
`ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb`.
Ein abweichender vorhandener Cache wird mit Fehler erhalten. CPU-Bibliotheken
werden statisch mitgebaut; BLAS und GPU-Backends sind für diesen Kandidaten
abgeschaltet. Dies ist noch keine geprüfte Distributions-/ABI-Kompatibilität.

Der Prozess lässt sich hinter denselben Supervisor setzen:

```sh
python3 runtime/diktat_runtime.py --capture \
  'arecord -q -f S16_LE -r 16000 -c 1 -t raw' -- \
  build/whisper-resident/diktat-whisper build/ggml-small-q5_1.bin
```

Dieser Befehl startet ein echtes Mikrofon nur bei bewusster Ausführung. Die
berichteten automatischen Abnahmen verwenden ausschließlich Dateiquellen.
Modellwahl im Launcher, Doctor, Installationspakete und Ereignisschnittstelle
sind noch nicht für diesen Kandidaten integriert.

## Stop-Verhalten

Reguläres EOF verarbeitet das verbleibende vollständige Segment, beendet den
Leser und gibt den Modellkontext frei. Ungerade PCM-Bytes, Lesefehler,
Decode-Fehler und fehlerhafte Ausgabe sind fehlgeschlagene Läufe.

Bei **SIGTERM/SIGINT** beendet der isolierte Prozess sich sofort mit Exit 143/130
über das POSIX-signalsichere `_exit`. Das Betriebssystem gibt Threads, Speicher
und Dateideskriptoren frei. Es gibt dann keinen abschließenden Decode und keinen
vollständigen erfolgreichen Audiobilanz-Trace. Der externe Supervisor beendet
zusätzlich die von ihm gestartete Aufnahme samt Prozessgruppe.

Diese Entscheidung folgt einem realen Befund: Der erste Kandidat vertraute auf
den Engine-Abbruchcallback. Beim Mac-Test blieb er nach SIGTERM länger als eine
Sekunde aktiv und musste hart beendet werden. Die Prozessgrenze macht Stop
unabhängig davon, wann eine interne Rechenphase den Callback abfragt. Der Callback
bleibt für bereits erkannte Eingabefehler aktiv. Die physische Mikrofon-/Desktop-
Stop-Abnahme ist davon getrennt und bleibt offen.

## Reproduzierbare Tests

```sh
python3 -m unittest discover -s tests -p 'test_whisper_resident.py' -v
```

16 Tests kompilieren den tatsächlichen Frontend-Code mit ASan/UBSan gegen eine
kontrollierte Engine-API. Geprüft werden 20 Segmente bei einem Modellladevorgang,
Puffergrenzen, 28-s-Fenster, Unicode-Zeilen, fragmentiertes PCM, Teilframes,
Eingabe-/Ausgabefehler, ungültige Parameter sowie Stop während Leerlauf/Decode.
Diese Tests liefern keine WER-Aussage. Der separate reale Build prüft die
API-Kompatibilität mit der gepinnten Engine.

Der manuell mit `run_resident=true` gestartete GitHub-Workflow `quality-audit` ruft den wiederverwendbaren
`resident-audit` auf dem vorhandenen Ubuntu-CPU-Agenten auf. Fremder PR-Code wird
weiterhin nicht auf diesem Agenten ausgeführt. Neben dem bisherigen Geist-Pilot
werden beide Whisper-Beamvarianten auf zwölf sauberen und sechs 10-dB-Fällen
geprüft, gefolgt von einer zeitgetreuen Sitzung und einem realen Stop-Test.
Der Kandidatenvergleich ersetzt die Sprachevidenz des Release-Standards nicht.
Er ist standardmäßig ausgeschaltet, damit ein absichtlich schwächerer Vergleichs-
kandidat keinen späteren Release eines separat freigegebenen Standards blockiert.

`benchmarks/resident_session.py` setzt die zwölf menschlich gelesenen Aufnahmen
mit je einer Sekunde Pause zu 193,56 s zusammen. Es prüft einmaliges Modellladen,
Ende ohne Überlast und identische Byte-/Samplebilanzen von Quelle, Supervisor und
Core. Nur vollständige Läufe bekommen eine WER-Auswertung. Auf Linux wird das
Prozessbaum-RSS alle 250 ms gesampelt. Dies ist ein zusammengesetzter Lesesprache-
Belastungstest, kein natürliches Gespräch und keine physische Mikrofonabnahme.

`benchmarks/resident_stop.py` sendet SIGTERM, nachdem der Trace den Beginn eines
realen Decodes zeigt. Es misst Exitzeit und zusätzliche Ausgabebytes. Der Test
enthält weder GUI-Zielwechsel noch Mikrofon-Treiberfreigabe.

## Messergebnisse vom 7. September 2026

Code `46a284555c7fe9666442625b311b26e7900a3f14`,
[GitHub-Lauf 34062909992](https://github.com/geisten/geist-diktat/actions/runs/34062909992).
117 Tests bestehen lokal auf macOS und auf Ubuntu 24.04 x64/ARM64, einschließlich
des neuen C/Python-Uhrentests. Die realen ASR-Zahlen stammen vom eigenen x64-
Ubuntu-CPU-Agenten; dessen Kernel-/libc-Profil steht im Report. Sie ersetzen
keine Abnahme eines eingefrorenen Desktop-/Hardwareprofils.

| Ubuntu CPU, vier Threads | Saubere WER | 10-dB-WER | Saubere RTF | Max. Prozess-RSS |
|---|---:|---:|---:|---:|
| Resident small Q5_1, Beam 1 | 9,52 % | 32,31 % | 0,150 | 349,44 MiB |
| **Resident small Q5_1, Beam 5** | **8,84 %** | **24,62 %** | **0,173** | **465,82 MiB** |

Je Konfiguration wurden zwölf saubere und sechs verrauschte Clips vollständig
verarbeitet. Die saubere RTF umfasst Prozess-/Modellstart je Datei bei warmem
OS-Cache. Der 10-dB-RTF beträgt 0,128 (Beam 1) bzw. 0,152 (Beam 5).
Der gewählte Entwicklungskandidat ist **Beam 5**: 26/294 saubere und 32/130
verrauschte Wortfehler. Er besteht beide Pilotgrenzen; Beam 1 verfehlt die
Rauschgrenze. Bei 10 dB würde ein zusätzlicher Fehler bereits zum Nichtbestehen
führen. Ein repräsentatives, unabhängiges Freigabeset bleibt erforderlich.

| Zeitgetreue Beam-5-Sitzung | Ubuntu-Agent | macOS |
|---|---:|---:|
| Zugespieltes Audio einschließlich eingefügter Pausen | 193,56 s | 193,56 s |
| Gesamtdauer einschließlich Start und Aufräumen | 194,38 s | 195,95 s |
| Modellladevorgänge / finale Textzeilen | 1 / 19 | 1 / 19 |
| WER über die gesamte vollständige Sitzung | 8,84 % | 8,84 % |
| Gesampelte Spitze des Prozessbaums | 494,30 MiB | nicht gemessen |
| Eigene Supervisor-Queue, beobachtete Spitze | 640 Bytes | 18.560 Bytes |
| Unbestätigte Eingabebytes / Überlastabbruch | 0 / nein | 0 / nein |

Beide Sitzungen bestätigen exakt 6.193.920 Bytes von Quelle und Supervisor bis
zu 3.096.960 vom Core gelesenen Samples. Gleicher SHA-256 der zusammengesetzten
Aufnahme belegt gleichen Audioinhalt trotz verschiedener lokaler Manifestumfänge.
Das ist ein bestandener Transport-/Sitzungstest. Es ist kein Nachweis für
verlustfreie Mikrofonhardware, 60-Minuten-Stabilität oder fehlende Wortfehler.
Der reale Stop benötigt **15,30 ms auf Ubuntu und 4,58 ms auf macOS**, jeweils
Exit 143 und null zusätzliche Ausgabebytes. Das sind Einzelmessungen im Decode,
kein p95 einer umfassenden Stop-/GUI-Matrix.

Der frühere Mac-Sitzungstrace zeigte unterschiedliche C/Python-Zeitbasen:
Darwins `CLOCK_MONOTONIC` und Pythons `mach_absolute_time` waren nach Systemschlaf
gegeneinander versetzt. Der C-Trace verwendet auf macOS jetzt ebenfalls
`mach_absolute_time`, unter Linux weiterhin `CLOCK_MONOTONIC`. Die letzte
Mac-Sitzung wurde mit dieser Korrektur vollständig neu ausgeführt. Ältere
Mac-Traces erlauben keine komponentenübergreifende Latenzberechnung; die vorher
geprüfte Bytebilanz und WER waren davon unabhängig.

Der Gesamtworkflow bleibt rot, weil der noch ausgelieferte Geist-Standard seine
Sprachgrenzen und Beam 1 die Rauschgrenze verfehlen. Beim ausgewählten Beam 5 sind
Gate-Checker, Sitzung und realer Stop erfolgreich. Der Vergleichsjob verlangt
weiterhin beide experimentellen Gate-Ergebnisse; er ist im normalen manuellen
Release-Evidenzlauf standardmäßig nicht eingeschaltet. Der Standard wurde nicht
stillschweigend umgestellt und es wurde kein Release veröffentlicht.

Die dauerhafte [numerische Evidenz](../benchmarks/reports/m2-2026-09-07/index.json)
enthält Einzelwerte, Hashes, Gates, Sitzungs-/Stopberichte, die historischen
Stop-Fehlmessung und die Zuordnung der Workflowfehler. Corpus-Audio und
Transkripte sind nicht enthalten.
