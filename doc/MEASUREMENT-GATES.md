# Verbindliche Sprachgates und Messung bis zur Texteingabe

Implementierung: `d274352`, Testablauf korrigiert bis `9968fea` (6. September 2026). Die neuen Prüfungen sind ein
Teil von M1 im [Produktplan](PRODUCT-PLAN.md). Sie ersetzen weder die fünf
zugesagten App-Abnahmen noch den externen [Nutzennachweis](BETA-PILOT.md).

## Sprachqualität und Veröffentlichungsweg

Der manuell gestartete `quality-audit`-Job auf dem Ubuntu-CPU-Agenten verarbeitet
jetzt zwölf saubere FLEURS-Aufnahmen und sechs daraus abgeleitete 10-dB-Rauschfälle.
Danach führt er `benchmarks/check_gates.py` zwingend aus, auch wenn die Erkennung
vorher fehlgeschlagen ist. Alte Ergebnisdateien des eigenen Testlaufs werden vor
Beginn entfernt. Fehlende neue Ergebnisse können damit keine alten grünen Werte
wiederverwenden.

Der Checker verlangt:

- Vollständige erfolgreiche Gruppen, mindestens 12/6 Clips und 294/130 Referenzwörter.
- Saubere WER ≤10 % und 10-dB-WER ≤25 %.
- Eindeutige Clip-IDs, Audiohashes, positive Referenzlängen, gültige Editierfehler-
  und Zeitangaben; keine negativen, booleschen oder nichtendlichen Zahlen als Messwerte.
- Übereinstimmung zwischen den einzelnen Clipwerten und sämtlichen berichteten
  Gruppensummen; ein schönerer zusammengefasster WER-Wert reicht nicht.
- Commit-, Manifest-, Binary- und Modellhashes sowie enginespezifische Dateien.
  Im CI muss der Report exakt zum aktuellen Commit gehören.

Ein Fehler erzeugt Exit 1 und einen maschinenlesbaren Bericht. Der Sprachjob darf
mit dem aktuellen Standardmodell fehlschlagen; die Grenze wird nicht an das
Modellergebnis angepasst. Der FLEURS-/Rauschpilot bleibt ein **Entwicklungsset**,
kein unabhängiger Nachweis repräsentativer DACH- oder Alltagsqualität.

Vor einer tagbasierten Veröffentlichung benötigt der bestehende `release`-Workflow
nun zusätzlich `quality-evidence`. Dieser Job sucht den jüngsten manuell gestarteten
`quality-audit`-Lauf für exakt denselben Commit, verlangt dessen Erfolg, lädt dessen
Sprachartefakt und wertet es erneut mit der aktuellen Policy aus. Ein älterer grüner
Lauf ersetzt keinen neueren fehlgeschlagenen oder noch laufenden Lauf. Fehlende oder
abgelaufene Artefakte blockieren die Veröffentlichung. Der Prüfer veröffentlicht
selbst nichts und benötigt nur Lesezugriff auf Actions.

Das ist eine technische Sprach-Voraussetzung. Der externe Pilot, unabhängige
Sprachdaten, vollständige Desktop-Abnahme und Nachweis mit den konkreten
Auslieferungsartefakten bleiben weitere Release-Arbeiten. Ein erfolgreicher
Sprachjob allein ist keine vollständige Beta-Freigabe.

## Opt-in-Diagnose entlang des Audiopfads

`GEIST_DIKTAT_TRACE=/absoluter/pfad/trace.jsonl` aktiviert numerische Diagnoseevents.
Pro kontrollierter lokaler Sitzung muss eine **neue, leere Datei** verwendet werden.
Die Datei enthält weder Audio noch Transkript. Sie ist eine interne Messschnittstelle,
nicht der noch zu entwickelnde öffentliche Zustands-/Ergebnisvertrag. Die kontrollierte
Dateiquelle gibt jeden vollständigen 20-ms-Block erst an dessen zeitlichem Ende frei.

Ohne diese Variable werden keine Tracedateien angelegt. Python- und C-Komponenten
verwenden dieselbe lokale monotone Uhr. Prozesse von verschiedenen Rechnern oder
getrennte Sitzungen dürfen nicht in einer Zeitachse vermischt werden. Die zusätzliche
Datei-I/O kann Messungen beeinflussen; Tracing und normale Durchsatzmessungen getrennt
kennzeichnen. Ungültige/unvollständige Traces gelten nicht als bestandene Abnahme.

| Komponente | Messpunkt / Bedeutung |
|---|---|
| Kontrollierte Dateiquelle | Ursprung der zeitgetreuen Audioachse, gesendete Bytes und maximale Verspätung der Quelle |
| Supervisor | Empfangene und in die Decoder-Pipe geschriebene Bytes, Queue-Spitze, maximales Queue-Alter und blockierte Schreibzeit, unbestätigte Bytes/Fehler |
| Core | Modellladen/-bereitschaft, Decode-Beginn/-Ende je Äußerung, fertig vorbereitete und ausgegebene Textnachricht, gesamte gelesene Samplezahl |
| IBus | Text-Commit angefordert; noch keine Bestätigung aus der Anwendung |
| GTK-/Qt-Testanwendung | Textfeldänderung tatsächlich beobachtet |

Bytes in einer Betriebssystem-Pipe sind noch kein vom Core verarbeitetes Audio.
Der Analyzer vergleicht deshalb die Bytebilanz der Quelle/des Supervisors mit der
Samplebilanz des Cores. Ein abgebrochener oder unvollständiger Pfad erhält keine
erfolgreiche Live-Kennzahl. Queue-Messwerte decken den eigenen Benutzerpuffer ab;
Quelle und Core zeigen zusätzlich Rückstand oder Verlust außerhalb dieses Puffers.
Die interne Aufteilung des Engine-Encoders/Decoders und Prozessbaum-RSS-Messung
sind damit noch nicht vollständig instrumentiert.

## Latenz bis zum Textfeld

`benchmarks/latency.py` benötigt zusätzlich unabhängig festgelegte Sprachendpunkte
als Sample-Indizes. Es verwendet **nicht** automatisch den RMS-VAD-Endpunkt als
menschliche Referenz. Jede erwartete Ausgabe braucht eine vorbereitete und tatsächlich
emittierte Core-Nachricht sowie eine Beobachtung im Textfeld mit passender Sequenz.
Nur stdout oder ein IBus-Commit können die Prüfung nicht bestehen.

`p95_insertion_s` ist der Abstand zwischen annotiertem Sprachende auf der Audioachse
und der tatsächlichen Textfeldänderung; p95 verwendet die Methode „nearest rank“.
Zusätzlich wird der Abstand zwischen vorbereiteter Decoder-Ausgabe und Textfeldänderung
angegeben. Der Zeitpunkt nach `fflush` kann durch Scheduling bereits hinter einer
Anwendungsreaktion liegen; daher beginnt dieses Teilintervall vor dem Schreiben,
während eine separate erfolgreiche Ausgabe weiterhin nachgewiesen werden muss.

Die vorhandenen GTK-/Qt-Probes beobachten jeweils eine eingefügte Zeile. Ein p95
über genau eine Probe entspricht diesem Einzelwert und ist **kein** belastbarer
p95 über Alltagsdiktate. Mehrteilige Sitzungen, echte Mikrofone und die fünf
Beta-Anwendungen benötigen weitere Beobachter und ausreichend annotierte Daten.

## Reproduzierbare Prüfung

Im vorbereiteten isolierten Ubuntu-Testsystem:

```sh
sh tests/ubuntu.sh
```

Das führt zusätzlich `tests/toolkit_latency.sh gtk` und `qt` aus. Jeder Test spielt seine annotierte Aufnahme genau einmal zu, auch wenn IBus beim Fensterabbau erneut aktiviert wird. Der Analyzer wartet begrenzt auf die abschließende Laufzeitbilanz; das Schließen des Testfensters beweist noch kein vollständig beendetes Aufnahmesystem. Die Kette benutzt
zeitgetreues synthetisches PCM, den echten Supervisor, den echten Core mit kontrollierter
Engine-API, IBus und echte Textfelder unter privatem D-Bus/Xvfb. Das Sprachende der
synthetischen Probe ist unabhängig festgelegt. Der Test prüft Messinstrumentierung
und Transport; er liefert keine ASR-WER oder physische Mikrofonfreigabe.

Ergebnisse liegen unter `tests/results/`: `gtk-latency.json`, `qt-latency.json`,
numerische Traces und Logs. Der echte Sprachjob erzeugt separat
`ubuntu-agent-quality.json` und `speech-gates.json`. Actions-Artefakte bleiben
zeitlich begrenzt verfügbar; dauerhafte ausgewählte numerische Evidenz wird im
Repository unter `benchmarks/reports/` archiviert, ohne Corpus-Audio oder Transkripte.

## Abnahme auf `9968fea`

[GitHub-Lauf 34054971819](https://github.com/geisten/geist-diktat/actions/runs/34054971819):
Ubuntu 24.04 x64 und ARM64 bestehen jeweils **100 unittest-Fälle** sowie die
isolierten IBus-/GTK-/Qt-Prüfungen. Lokal auf macOS bestehen dieselben 100 Fälle.
Die Ubuntu-Coverage des tatsächlichen Cores mit kontrollierter Engine beträgt
**98,18 % Zeilen, 73,76 % Zweige und 100 % Funktionen** auf beiden Architekturen.

| Kontrollierte Einzelprobe | x64 | ARM64 |
|---|---:|---:|
| Sprachende bis GTK-Textfeld | 0,80130 s | 0,80133 s |
| Sprachende bis Qt-Textfeld | 0,80153 s | 0,80187 s |

Jede Probe bestätigt 41.600 Bytes durch Quelle und Supervisor bis zu 20.800 vom
Core gelesenen Samples, ohne unbestätigte Bytes. Die rund 0,80 s enthalten die
konfigurierte Sprechpausenerkennung bei kontrollierter Engine. Sie belegen weder
die Modellgeschwindigkeit noch das p95-Tor für echte Diktate.

Der eigene Ubuntu-CPU-Agent verarbeitet alle 18 Sprachfälle erfolgreich, verfehlt
aber beide WER-Ziele:

| Entwicklungsgruppe | Fehler / Referenzwörter | WER | Grenze | RTF |
|---|---:|---:|---:|---:|
| Saubere Lesesprache, 12 Clips | 47 / 294 | 15,99 % | ≤10 % | 0,387 |
| Simuliertes Rauschen 10 dB, 6 Clips | 46 / 130 | 35,38 % | ≤25 % | 0,442 |

Maximales gemessenes RSS eines Erkennungsprozesses: 6.233,32 MiB. Frische Prozesse
pro Datei, warmes OS-Dateicache; kein gleichzeitig summiertes Prozessbaum-RSS.
Daher ist der Sprachjob und damit der Gesamtworkflow **korrekt fehlgeschlagen**.
Provenienz, Einzelwerte und Summenkonsistenz bestehen. Der Release-Prüfer wurde
lesend gegen diesen abgeschlossenen Lauf ausgeführt und lehnt ihn mit Exit 1 ab;
eine Veröffentlichung wurde nicht ausgeführt.

Die vorangegangenen Läufe
[34054366163](https://github.com/geisten/geist-diktat/actions/runs/34054366163) und
[34054617782](https://github.com/geisten/geist-diktat/actions/runs/34054617782)
deckten Fehler im neuen Testablauf auf: erneute IBus-Aktivierung beim Fensterabbau
und Auswertung vor der abschließenden Laufzeitbilanz. Die einmalige Zuspielung,
begrenzte Wartephase und Block-Endzeit-Korrektur beheben diese Fehler; die strikten
Vollständigkeitsprüfungen bleiben erhalten.

Dauerhafte [numerische Evidenz mit Hashindex](../benchmarks/reports/m1-2026-09-06/index.json)
enthält Sprachreport, Gate-Ergebnis, abgelehnte Release-Prüfung, Textfeldmessungen,
Traces und unabhängige Annotation. Audio und Transkripte sind nicht enthalten.
Die CI-Evidenz gilt für den genannten Codecommit; ein späterer Kandidat benötigt
auch bei reinen Dokumentationsänderungen einen eigenen erfolgreichen Lauf.
