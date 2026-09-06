# Umsetzung und Abnahme am 6. September 2026

## Ergebnis

Die priorisierten Stabilitätskorrekturen sind implementiert. Es gibt asynchrone
Vim-/Neovim-Adapter, paketierte Editorinstallation, Diagnose, einen begrenzten
Capture-Supervisor, einen zeilenweisen Ausgabeadapter und eine baubare macOS-
Menüleisten-App. **Der Gesamtplan ist damit noch nicht produktfertig abgeschlossen.**
Erkennungsqualität unter Rauschen, kontinuierliches Pi5-Diktat, repräsentative
DACH-Daten, breite Desktop-Abnahme und notarisiertes macOS-Deployment bleiben offen.

Die Änderungen liegen isoliert auf `codex/product-readiness`, aufbauend auf dem
Audit-Branch aus PR #41. Der laufende ursprüngliche Arbeitsbaum wurde nicht
überschrieben. Nach ausdrücklicher Nutzerfreigabe wurde der Branch gepusht.
Der [GitHub-Lauf 34020085582](https://github.com/geisten/geist-diktat/actions/runs/34020085582)
auf `5e27010c461a6cff4ba830af52bf78df94cc7213` ist vollständig erfolgreich:
Ubuntu x64 und ARM64 je 77 Tests, dazu reale deutsche ASR auf dem eigenen CPU-Agenten.
Der aktualisierte [Produktplan](PRODUCT-PLAN.md) trennt erledigte Arbeiten von
verbleibenden Freigabetoren; die [SOTA-Analyse](RELEASE-STRATEGY-2026-09-06.md)
begründet die nächsten Architektur- und Modellvergleiche.

## Implementiert

| Aufgabe | Umsetzung | Abnahmestand |
|---|---|---|
| #16 / #17 | EOF und vollständige PCM-Teilframes bleiben erhalten; Stream-/Decode-Fehler sind Fehler | ASan/UBSan-Regressionen grün |
| #18 / #37 | Recorder und Decoder separat überwacht; standardmäßig 6 s eigene Audioqueue; Exit 75 bei Überlast; TERM/KILL für eigene Gruppen | Fehler, später Recorder-Exit, störrische Nachfahren und echte zeitgetreue Aufnahmezufuhr getestet; residenter Decoder bleibt offen |
| #19 / #20 / #24 / #27 | Neovim-Framing, Sitzungskennung, begrenzte Queue, Moduswechsel, Fehleranzeige, portabler Launcher | Callback-Verträge, echter fragmentierter Prozess, Undo und 100 Wechsel grün |
| #21 | Archiv zunächst entpacken/validieren; atomarer Verzeichnistausch; Vorversion sichern; Installationssperre | Prüfsummen-, Entpack-, Commitfehler, Update und konkurrierende Sperre getestet |
| #22 | Git-Arbeitsbäume mit `.git`-Datei akzeptiert; keine rekursive Löschung bestehender Engine-Verzeichnisse; temporärer Erst-Clone | Offline- und bestehender Checkout getestet |
| #23 | GLib-Child-Watch, Reaping, EOF/HUP-Ausgabe, begrenzter Stop und Neustart | 100 Zyklen und echte IBus-Objekte grün |
| #25 / #26 | Vollständige UTF-8-Codepoints auch über Token-Grenzen; strikte RMS-Eingabe | Grenzen, fehlerhafte Eingaben, ASan/UBSan grün |
| #28 / #29 | Vim `job_start`-Adapter; native `pack`-Installation für beide Editoren | Leeres HOME, erhaltene Vorversion, echte Unicode-Pipe, 100 Vim-Zyklen; keine vimrc-Änderung |
| #30 | `doctor [--json] [--verify]`, klarere Setup-Hinweise, SHA-geprüfte temporäre Downloads | Diagnose und Installation geprüft; geführte Mikrofonwahl und menschlicher One-Click-Test offen |
| #31 / #35 | IBus stoppt bei Fokusverlust/Disable; Passwort, PIN und Private-Flag sperren Aufnahme | GTK3/Qt5/Xvfb und Schutzfeldtests grün; Wayland/Browser/Flatpak-Matrix offen |
| #32 | Swift-Menüleisten-App: Einrichtung, Diagnose, Vorschau, Kopieren, Hotkey, optionales AX-Einfügen; beaufsichtigter Prozessbaum | Build, ad-hoc-Signatur und Framing-Selbsttest grün; GUI-/Berechtigungs-/App-Matrix und Notarisierung offen |
| #33 / #34 | Zeilenweiser argv-Adapter und dokumentierter Prozessvertrag; keine Shell-Auswertung des Transkripts | UTF-8, Sonderzeichen, große Zeilen und fehlerhafte Senken getestet |
| #36 / #38 / #39 | Vergleichsadapter für gepinntes whisper.cpp, WER-Gates, Rausch-/Dialektvergleich und Beam-A/B | Messwerte unten; Standardbackend bleibt Geist, Qualitätsdefekte bleiben offen |
| #40 | Backend-Reihenfolge NEON → x86 → Scalar | Auswahlvertrag sowie neuer realer x64-ASR-Lauf grün; Qualitätsgrenze bleibt verfehlt |

Der Tarball-Installer verwendet unter macOS `renamex_np(RENAME_SWAP)` und unter
Linux `renameat2(RENAME_EXCHANGE)`. Ein Erstinstall verwendet NOREPLACE/EXCL.
Dadurch gibt es auch beim Austausch einer bestehenden Verzeichnisinstallation
kein Fenster ohne Zielverzeichnis. Die Vorversion bleibt als `.previous` erhalten;
bei Unterbrechung kann sie noch unter dem angezeigten `.geist-diktat.*`-Stagingnamen
liegen. Nicht unterstützte Dateisysteme/Plattformen brechen mit erhaltener Vorversion
ab. Eine nach SIGKILL verbliebene Installationssperre muss manuell geprüft werden.

## Tests und Artefakte

- macOS: **77 Python-unittest-Fälle bestanden**, darunter 26 Core-Fälle mit ASan/UBSan;
  zusätzliche Einzelprüfungen innerhalb dieser Fälle sind nicht als eigene Tests gezählt.
- Ubuntu 24.04 ARM64 im isolierten Pi-Container: **77 Fälle bestanden**, einschließlich des zweiten echten Vim-Stresstests und des
  atomaren Linux-Verzeichniswechsels.
- IBus: Prozessreaping nach regulärem Ende, 100 Start/Stop-Zyklen, Neustart,
  Passwort/PIN/Private, Fokusverlust und Disable bestanden.
- Echte GTK3- und Qt5-Textfelder unter Xvfb erhalten Unicode über IBus.
- .deb aus Quellen gebaut, in einem wegwerfbaren Container per apt installiert;
  Core/Launcher, Editorpakete und Installation in leerem HOME geprüft.
- Endgültiger Core zusätzlich auf macOS und Pi5 mit je zwei echten deutschen
  Aufnahmen ausgeführt: reguläre Exits und exakt gleiche Transkripte wie in den
  jeweiligen plattformspezifischen Vergleichsläufen. Dies ist ein Regressionstest,
  keine erneute repräsentative WER-Schätzung.
- macOS-Tarball gebaut und auf unerwartete dynamische Bibliotheken geprüft.
  Swift-App gebaut, ad hoc signiert; UTF-8-Framing, EOF und Puffergrenze selbstgetestet.
- LLVM-Coverage des tatsächlichen `src/diktat.c` mit kontrollierter Engine:
  **98,08 % Zeilen, 73,27 % Zweige, 100 % Funktionen**. Diese Zahlen erfassen keine
  Modellqualität, Mikrofontreiber, GUI oder vollständige geistlib-Abdeckung.

Der 30-Minuten-Stresstest verarbeitet 1.400 synthetische Äußerungen mit einer
kontrollierten Engine. Er ist ein Lifecycle-Test, **kein 30-minütiger ASR- oder
physischer Mikrofontest**. Alle Sprachaufnahmen werden aus Dateien zugespielt.

## Nachgetragene GitHub-Ubuntu-Abnahme

Der oben verlinkte Lauf endete am 6. September 2026 um 07:49:02 UTC erfolgreich.
Die beiden gehosteten Ubuntu-Jobs bestanden jeweils 77 Fälle einschließlich
isolierter IBus-/GTK-/Qt-Prüfungen. Ubuntu-Core-Coverage: **98,08 % Zeilen,
73,50 % Zweige, 100 % Funktionen**, wiederum mit kontrollierter Engine.
Die leichte Abweichung zur macOS-Zweigabdeckung ist kein neuer Modelltest.

Der eigene Ubuntu-CPU-Agent erkannte zwölf deutsche FLEURS-Aufnahmen mit Geist/Gemma:
294 Referenzwörter, 47 Fehler, **15,99 % WER**. 181,56 s Audio benötigten insgesamt
70,44 s, entsprechend **RTF 0,388** einschließlich Prozessstart. Maximales RSS:
6.232,96 MiB, also rund **6,09 GiB**. Das saubere Pilotziel ≤10 % bleibt verfehlt.
Dateizuspielung mit frischen Prozessen/warmem OS-Cache ist keine physische
Daueraufnahme und keine gemessene Einfügelatenz.

## Neue Pi5-Messwerte

Pi5 mit 4 GiB RAM, vier Threads, CPU. Gleiche zwölf menschlich gesprochenen
FLEURS-Aufnahmen, 294 Referenzwörter, 181,56 s Audio; frischer Prozess je Aufnahme,
warmes Betriebssystem-Dateicache. RTF = gesamte Laufzeit / Audiozeit, inklusive
Start und anhängender VAD-Stille. Eine kleinere Zahl ist schneller.

| Variante | WER | Gesamtlaufzeit | RTF | Spitzen-RSS |
|---|---:|---:|---:|---:|
| Geist/Gemma Q4_K_M | 20,75 % | 277,22 s | 1,53 | 2.893,7 MiB |
| whisper.cpp small Q5_1, Beam 5 | 8,84 % | 200,29 s | 1,10 | 462,4 MiB |
| whisper.cpp small Q5_1, Beam 1 | 9,52 % | 172,93 s | 0,95 | 347,5 MiB |

Beim Whisper-Adapter wird das Modell für jedes VAD-Segment neu geladen. Die RSS-
Angabe stammt aus `wait4` und ist kein gleichzeitig aufsummierter Prozessbaumwert.
Das gesonderte Live-Experiment sampelt dagegen den Prozessbaum aus `/proc`.
Beam 1 verändert gegenüber Beam 5 nur die Suchbreite/Strategie; zwei zusätzliche
Wortfehler stehen 13,7 % weniger Zeit und rund 24,8 % weniger Spitzen-RSS gegenüber.
Die gewünschte Durchsatzreserve RTF ≤0,8 erreicht keine dieser Pi5-Konfigurationen.

Geist unter simuliertem Mikrofonrauschen (sechs gleiche Inhalte je Bedingung):
20 dB **13,85 %**, 10 dB **37,69 %**, 5 dB **68,46 % WER**. Das bestätigt die früheren
Pi5-Pilotwerte. Alle 30 Läufe enden regulär. Diese Serie verwendet den ersten
Stabilitätsstand; die anschließende UTF-8-Tokenzusammenführung wurde zusätzlich
mit Regressionen und dem realen Live-Pfad geprüft. Die Binärhashes im JSON machen
die Stände unterscheidbar; hier wird kein identischer Build behauptet.

## macOS und Dialekte

Die neue Geist-Serie wurde nach neun vollständigen Aufnahmen abgebrochen, weil
fremde Engine-Stresstests dauerhaft sechs bis acht Kerne beanspruchten. Die Daten
sind ausdrücklich als Konkurrenzlast markiert und **keine Geschwindigkeitsbasis**.
Auch die neuen Mac-Whisper-Zeiten erlauben daher keine Aussage über einen unbelasteten
Mac. Die ursprüngliche vollständige Geist-Pilot-WER lag bei 16,0 %.

Der validierte Whisper-Pfad erreicht auf dem Mac mit zwölf sauberen Aufnahmen
**8,84 % WER**; unter 20/10/5 dB Rauschen **13,08 / 26,15 / 54,62 %**. Damit besteht
er das vorgeschlagene saubere Pilotziel von 10 %, verfehlt das 10-dB-Ziel von 25 %.
Die ersten Adapterversuche lieferten wegen einer falschen stdout-Konfiguration
leere Ausgaben. Diese Instrumentierungsfehler wurden korrigiert, mit echter
Sprachausgabe geprüft und vollständig neu gemessen; sie sind aus den berichteten
ASR-Ergebnissen ausgeschlossen.

16 SwissDial-Samples aus acht Schweizer Varianten ergeben beim Whisper-Pfad
**57,59 % WER gegen die hochdeutsche Referenz** und **77,64 % gegen die Dialektschreibung**.
Diese beiden Aufgaben sind getrennt zu beurteilen. Zwei Inhalte pro Variante und
fehlende unabhängige Sprecherabdeckung erlauben keine allgemeine Dialektbewertung.
Für österreichische und deutsche Regionaldialekte fehlen weiterhin passende,
freigegebene und referenzierte Aufnahmen. **DACH ist noch nicht breit abgedeckt.**

## Zeitgetreue Gesprächszufuhr

Quelle ist ein echtes längeres deutsches Zweipersonengespräch; die Zuspielung
verwendet 20-ms-Blöcke im natürlichen Tempo. Kein physisches Mikrofon ist beteiligt.

- Geist stoppt nach **34,18 s** mit Exit **75**; Spitzenwert des gesampelten
  Prozessbaums **2.837,7 MiB**.
- Whisper Beam 5 stoppt nach **31,84 s** ebenfalls mit Exit **75**;
  Prozessbaum-Spitzenwert **498,6 MiB**.
- Whisper Beam 1 stoppt nach **31,88 s** ebenfalls mit Exit **75**;
  Prozessbaum-Spitzenwert **383,2 MiB**.

Das ist ein bestandener Test des **kontrollierten Überlastverhaltens**, aber ein
nicht bestandenes Tor für kontinuierliches Diktieren. Es wird keine WER über
abgebrochene Gesprächsfragmente als reguläre Erkennungsleistung ausgegeben.

## Nächste Schritte zur Produktfreigabe

1. **Erledigt:** Branch gepusht; `quality-audit` auf dem Implementierungsstand
   erfolgreich ausgeführt (gehostetes x64/ARM64 und manueller CPU-Agent).
   **Neu offen:** Release-Qualitätsjob muss den vorhandenen WER-Gate-Checker
   verpflichtend ausführen und neben sauberer Sprache auch Rauschen prüfen.
   Der bisherige grüne Workflow misst WER, erzwingt aber keine WER-Grenze.
2. Die stabilisierten P1-Korrekturen und Editorpfade reviewen. Wiederherstellung nach unterbrochenen
   Installationen sowie breite Vim-/Neovim-Modus-/Fokusmatrix ergänzen.
3. Pi5: residenten ASR-Prozess, kürzere/überlappende Segmente und kleinere
   Modelle jeweils getrennt gegen WER **und** maximalen Decoder-Stillstand testen.
   Nur den Puffer zu vergrößern verdeckt lange Verzögerungen. Beam 1 ist ein
   messbarer Kandidat, keine Freigabe. Danach 30/60 Minuten physische Aufnahme mit
   Temperatur, Drosselung, Swap, Rückstand und p95-Latenz messen.
4. Unabhängiges DACH-Testset mit mehreren Sprechern pro Region und echter
   Mikrofon-/Umgebungsgeräuschstreuung einfrieren. Pilotdaten nicht zugleich für
   Parameterauswahl und abschließende Qualitätsbehauptungen verwenden.
5. GNOME Wayland/Xorg, KDE, GTK4/Qt6, Browser, Electron, LibreOffice und
   Flatpak/Snap samt Schutzfeldern und Gerätewechsel tatsächlich abnehmen.
6. Geführten Erststart, Mikrofonwahl, Update/Rollback/Deinstallation und Tests
   mit fünf Personen ohne Entwicklerkontext abschließen.
7. macOS-App mit vorhandener Developer-ID signieren/notarisieren und die
   Berechtigungs-/TextEdit-/Browser-/Terminal-Matrix testen. Aktuell sind auf
   diesem Mac **null gültige Codesigning-Identitäten** vorhanden.

Der derzeit belegte Mehrwert liegt in lokaler Verarbeitung, einem kleinen C-
Prozessvertrag und gezielter Editor-/IBus-Anbindung. Die Messung zeigt zugleich,
dass ein etablierter ASR-Backend im deutschen Pilot weniger Wortfehler und erheblich
weniger Speicher benötigen kann. Eine generelle Erkennungsüberlegenheit der
Geist-Lösung oder „One-Click“ ist weiterhin nicht nachgewiesen.

Numerische Evidenz ohne Audio/Transkripte: [product-2026-09-06.json](../benchmarks/reports/product-2026-09-06.json).
Bedienung und Schnittstelle: [EMBEDDING.md](EMBEDDING.md).
