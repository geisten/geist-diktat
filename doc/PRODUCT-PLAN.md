# Produktfreigabe: Stand und Reihenfolge

Stand: **6. September 2026**. Aktuell getesteter Code: `9968feacc575d99c4876f8b98b631f9bc8b1436f` (Stabilitätsbasis `5e27010`), Branch `codex/product-readiness`. Dieser Plan enthält die nach dem Grilling-Interview ausdrücklich bestätigten Produktentscheidungen und ersetzt die zuvor vorgeschlagene Freigabereihenfolge.

**Ziel ist die erste öffentliche Ubuntu-GNOME-Beta.** Ihre Blocker sind zuverlässiges Desktop-Diktat, deutsche Qualität für Alltags- und technische Texte, die fünf verbindlichen Anwendungen, geführter Erststart und der externe Zeitgewinn-Nachweis. Die Stabilitätsbasis ist umgesetzt; die Beta ist noch nicht freigegeben. Pi5, macOS und zusätzliche Desktop-Profile liegen außerhalb des kritischen Pfads. Breite DACH-Tests bleiben im Plan, Dialektunterstützung wird zunächst ausdrücklich experimentell ausgewiesen.

✅ = implementiert und im genannten Umfang getestet; 🟡 = teilweise umgesetzt; ⬜ = offen. Umsetzung auf dem Branch bedeutet nicht Merge, Veröffentlichung oder Feldabnahme. Die GitHub-Issues #16–40 waren bei der dokumentierten Abfrage vom 6. September weiterhin offen; dieses Planupdate schließt keine Issues.

Messungen: [Implementierungsbericht](IMPLEMENTATION-2026-09-06.md). Architekturentscheidung, Alternativen und aktuelle Primärquellen: [SOTA-Analyse](RELEASE-STRATEGY-2026-09-06.md).

## Bestätigte Produktentscheidungen

| Entscheidung | Verbindliche Festlegung |
|---|---|
| Produktzweck | Direktes Diktieren plus Einbettbarkeit für Entwickler; die eigenen Adapter verwenden denselben Prozessvertrag |
| Erste Plattform | Ubuntu GNOME; technisches Ausgangsprofil ist das bisher geplante Ubuntu 24.04 mit Wayland. Exakte OS-/App-/Paketversionen vor dem Pilot einfrieren |
| Verbindliche Anwendungen | Vim, Neovim, ein vorab festgelegter GNOME-Texteditor, Firefox, LibreOffice Writer |
| Entwicklerumfang | Lokaler Prozess: Audio hinein, Text und Zustandsereignisse heraus, Start/Stop und Fehlercodes. C-SDK und Netzwerk-API sind kein Beta-Versprechen |
| Inhalte | Deutsche Alltags- **und** technische Texte einschließlich englischer Fachbegriffe, Zahlen und Bezeichner |
| Dialektausgabe | Inhaltstreues Standarddeutsch ohne stilistische Umschreibung; wörtliche Dialektschreibung ist kein Produktmodus der ersten Beta |
| Engine | Beste nachgewiesene Lösung je Plattform; Geist/Gemma darf als Standard ersetzt werden |
| Bedienung | Shortcut startet/stoppt. Stabile Abschnitte nach Sprechpausen automatisch einfügen; vorläufigen Text nicht nachträglich im Zielfeld umschreiben |
| Beta und Aufmerksamkeit | Öffentliche Vorstellung, nachvollziehbare Ergebnisse/Demo und installierbarer Beta-Download starten gemeinsam |
| Vorabtest | Mindestens fünf externe Pilottester aus Germars Umfeld; Germar gewinnt sie, das Projekt liefert Ablauf und Auswertung |
| Veröffentlichungstermin | Erst nach bestandenen Kriterien; kein fester Termin auf Kosten der Abnahme |
| Pi5 und weitere Plattformen | Pi5 bleibt experimentell und blockiert die Ubuntu-Beta nicht. macOS und weitere Desktop-/App-Profile folgen separat |

### Verbindlicher Nutzennachweis vor dem öffentlichen Download

In **jeder** der beiden Kategorien Alltags- und technische Texte muss der Median
der personenbezogenen Zeitgewinne mindestens **25 %** betragen. Je Kategorie müssen
mindestens **vier von fünf Personen** schneller sein als beim Tippen. Die beiden
Kategorien werden weder miteinander noch über ihre Rohzeiten zusammengefasst.
Gemessen wird bis zum fertig korrigierten Text, einschließlich Start, Erkennung,
Einfügung und Nachbearbeitung. Verbleibende Inhaltsfehler dürfen keinen scheinbaren
Zeitvorteil erzeugen. Diese Kriterien sind beschlossen, aber noch nicht gemessen.

Das [Pilotprotokoll](BETA-PILOT.md) definiert Auswertung, Aufgabenvergleich und
Fehlerbehandlung. Technische Sprach-, Latenz-, Installations- und Sicherheitsgates
bleiben zusätzlich erforderlich. Der Zeitgewinn gegenüber Tippen ist kein Nachweis
für Überlegenheit gegenüber anderen Diktatprodukten.

## Bereits umgesetzt

| Status | Bereich / Issues | Nachgewiesene Umsetzung | Verbleibende Abnahme |
|---|---|---|---|
| ✅ | Core #16, #17, #25, #26, #40 | EOF/Teilframes, Fehlerstatus, UTF-8 über Token-Grenzen, RMS-Validierung, NEON/x86/Scalar-Auswahl | Regressionen bei Backendänderungen erhalten |
| ✅ | Installationssicherheit #21, #22 | Validiertes Staging, atomarer Austausch, Vorversion, Lock; vorhandene Engine-Checkouts erhalten | Komfortable Wiederherstellung unter M5 |
| ✅ | Aufnahmefehler #18 | Capture-/Decoder-Fehler sichtbar; eigene Prozessgruppen kontrolliert beendet | Physische Geräte-/Berechtigungsabnahme unter M4 |
| ✅ | Vim/Neovim #19, #20, #24, #27–29 | Asynchrone Adapter, UTF-8-Framing, Sitzungswechsel, begrenzte Ausgabequeue, native Paketinstallation | Breite interaktive Modus-/Fokusmatrix unter M4 |
| ✅ | IBus-Lifecycle #23 | Reaping, Stop/Neustart, EOF/HUP, 100 Wechsel | Weitere Desktop-Sitzungen unter M4 |
| ✅ | Pipeline #33 | Wörtliche zeilenweise UTF-8-Übergabe ohne Shell-Auswertung | Verfügbarkeit der Senke pro Desktop |
| ✅ | Tests / GitHub-Ubuntu-Agent | macOS und gehostetes Ubuntu x64/ARM64 je 100 Fälle auf `9968fea`; Pi-Ubuntu-Container historisch 77; echter x64-ASR-Pilot | GTK-/Qt-Testfelder geprüft; fünf Produkt-Apps, physische Mikrofone und Dauer-ASR offen |
| 🟡 | Supervisor / Pi5 #36, #37 | Capture entkoppelt, standardmäßig 6 s Queue, Überlast Exit 75; Whisper-/Beam-Vergleich | Kontinuierlicher Lesepfad und ausreichend schneller residenter Decoder fehlen |
| 🟡 | Sprache #38, #39 | 47 Pilot-Fixtures; WER-, Rausch-, Schweizer Dialekt- und Gesprächsmessungen; lokaler Gate-Checker | Unabhängiges DACH-Set und bestandene Qualitätsgates fehlen |
| 🟡 | Vertrag / Status #34, #35 | PCM16/UTF-8/Exitcode-Vertrag v1; IBus-Fokus-/Schutzfeldregeln | Zustandsereignisse, Teil-/Endergebnisse und globale Stop-Abnahme |
| 🟡 | Ubuntu-Apps #31 | Echte IBus-/GTK3-/Qt5-Prüfungen unter privatem D-Bus/Xvfb | GNOME Wayland/Xorg, KDE, moderne Toolkits und Sandbox-Apps |
| 🟡 | Erststart #30 | Doctor, SHA-geprüfte Modelldownloads, Setup, Editorinstallation | Mikrofonwahl, Fortschritt/Wiederaufnahme, Recovery, Nutzertests |
| 🟡 | macOS #32 | Swift-Menüleisten-App, Hotkey, Vorschau/Kopieren, optionales AX-Einfügen; Build/ad-hoc-Signatur grün | Native Capture-/Abhängigkeitslösung, GUI/TCC, Developer-ID/Notarisierung |

Der historische [GitHub-Lauf 34020085582](https://github.com/geisten/geist-diktat/actions/runs/34020085582) auf `5e27010` war vollständig grün. Ubuntu-Core-Coverage: **98,08 % Zeilen, 73,50 % Zweige, 100 % Funktionen**, mit kontrollierter Engine. Das erfasst keine Modell-, Treiber- oder vollständige Produktabdeckung.

**Historischer Stand dieses CI-Laufs:** Er maß WER ohne Gate-Aufruf. Mit `d274352` ist die verpflichtende Prüfung samt 10-dB-Gruppe implementiert; der tagbasierte Veröffentlichungsweg prüft erfolgreiche Sprachevidenz für denselben Commit. Die neue Messinstrumentierung ist in [MEASUREMENT-GATES.md](MEASUREMENT-GATES.md) beschrieben. Ein grüner Entwicklungs-Pilot allein bedeutet weiterhin keine vollständige Produktfreigabe.

Der aktuelle [Lauf 34054971819](https://github.com/geisten/geist-diktat/actions/runs/34054971819) auf `9968fea` besteht beide Vertragsjobs mit je 100 Fällen und den Textfeld-Latenzprobes. Core-Coverage: **98,18 % Zeilen, 73,76 % Zweige, 100 % Funktionen**. Der Sprachjob ist wegen **15,99 % sauberer und 35,38 % 10-dB-WER** korrekt rot. Die [numerische Evidenz](../benchmarks/reports/m1-2026-09-06/index.json) ist dauerhaft archiviert. M1 bleibt wegen der ausstehenden realen App-/Mikrofon-/Dauermessungen teilweise offen.

## Messungen, die die Priorität bestimmen

| Befund | Konsequenz |
|---|---|
| Pi5 Geist: 20,75 % WER, RTF 1,53, 2.894 MiB Spitzen-RSS | Standardpfad verfehlt Qualitäts- und Durchsatzziel |
| Pi5 Whisper small Q5_1: Beam 5 mit 8,84 % WER / RTF 1,10; Beam 1 mit 9,52 % / RTF 0,95 / 348 MiB | Bester bisher gemessener Pi-Kandidat; noch ohne Zeitreserve |
| Zeitgetreues Gespräch: Geist nach 34,18 s, Whisper nach ca. 31,9 s mit Exit 75 | Überlastbehandlung besteht; kontinuierliches Diktat fällt durch |
| Ubuntu-x64-Agent Geist: 15,99 % WER, RTF 0,388, ca. 6,09 GiB RSS | Durchsatz im Dateipilot gut; sauberes WER-Ziel verfehlt |
| Mac Whisper: 8,84 % saubere WER, 26,15 % bei 10 dB | Sauberer Pilot besteht; Rauschziel von 25 % verfehlt |
| SwissDial Whisper: 57,59 % gegen Hochdeutsch / 77,64 % gegen Dialektschreibung | Zwei verschiedene Referenzaufgaben; keine breite DACH-Freigabe |

Saubere Piloten: zwölf Aufnahmen, 294 Wörter; Rauschen: sechs Inhalte je Stufe. Pi-Zeiten enthalten Prozessstart; Whisper lädt bisher pro Segment neu. Mac-Vergleichszeiten standen unter Konkurrenzlast und sind keine Geschwindigkeitsbasis. Alle Sprachtests verwendeten Dateien. Der 30-Minuten-Test mit kontrollierter Engine ist ausschließlich ein Lifecycle-Test. Keine dieser Zahlen zertifiziert Alltagsqualität.

## Reihenfolge und Abnahmetore

Kritischer Pfad: **M1 Messung → M2 Ubuntu-Decoder → M4 fünf Anwendungen → M5 Erststart → M6 externer Pilot → M7 öffentliche Beta.** M3 stellt die unabhängigen Sprachdaten und Qualitätsgates bereit und beginnt mit M1; Germar gewinnt parallel die Pilottester. M0 sichert die Integration des Implementierungsstands. Pi5-Optimierung, macOS und zusätzliche Modellvergleiche dürfen diesen Pfad nicht verdrängen. Ein Termin ergibt sich erst aus bestandenen Toren.

### M0 — Stabilitätsbasis sichern: ✅ umgesetzt, Integration noch offen

- [x] Korrekturen, Adapter, Installer und Tests implementiert und gepusht.
- [x] GitHub-Ubuntu x64/ARM64 und manuellen CPU-Agent-Lauf erfolgreich ausgeführt.
- [ ] Änderungen reviewen und in den vorgesehenen Release-Branch integrieren. Issues erst nach passender Abnahme schließen; noch keinen Release-Tag setzen.

Evidenz: [Implementierungsbericht](IMPLEMENTATION-2026-09-06.md), [CI-Lauf](https://github.com/geisten/geist-diktat/actions/runs/34020085582).

### M1 — Freigabe messbar machen: 🟡 höchste nächste Priorität

Issues: [#34](https://github.com/geisten/geist-diktat/issues/34), [#36](https://github.com/geisten/geist-diktat/issues/36), [#38](https://github.com/geisten/geist-diktat/issues/38).

- [x] Pilotmanifest, numerische Reports, gepinnte Modelle/Engines, Gate-Checker vorhanden.
- [x] Ubuntu-Sprachjob um 10-dB-Rauschen und verpflichtenden Checker ergänzt; fehlende/fehlerhafte Clips, widersprüchliche Summen und falsche Commit-Zuordnung blockieren. Veröffentlichungsjob verlangt erfolgreiche Sprachevidenz für denselben Commit (`d274352`).
- [x] Numerische Evidenz des M1-Laufs dauerhaft mit Hashindex archiviert: Commit, Binary-/Modell-/Korpushashes, Einzelwerte, Gate-Ergebnisse, Textfeldtraces und Core-Coverage.
- [ ] Hardwaremodell, vollständige Decoderparameter und reale Auslieferungsartefakte für jedes zugesagte Release-Profil ergänzen. Die archivierten Entwicklungsmessungen ersetzen diese Zuordnung nicht.
- [x] Numerische Traces für Modellladen/-bereitschaft, Decode-Phasen, Ausgabe, IBus-Übergabe und beobachtete GTK-/Qt-Textfeldänderung implementiert. Latenzanalyse verlangt unabhängige Sprachendpunkte; v1-Textausgabe bleibt unverändert.
- [ ] Aufzeichnung auf die fünf Beta-Anwendungen und echte Mikrofone erweitern; Engine-interne Encoder-/Decoderanteile, kalte/warme Starts und ausreichend viele Äußerungen prüfen.
- [x] Byte-/Samplebilanz von Quelle, Supervisor und Core sowie Queue-Spitze/-Alter und blockierte Schreibzeit ergänzt; unvollständige/abgebrochene Audiozufuhr besteht die Latenzprüfung nicht.
- [ ] Prozessbaum-RSS, Stop-Zeit und langfristigen Rückstand im realen Dauerbetrieb vollständig erfassen. Trace-Probes mit kontrollierter Engine sind keine Dauer-ASR-Abnahme.

**Tor:** Ein absichtlich schlechter oder unvollständiger Report blockiert den Release-Job. Latenz ist bis zur Texteingabe messbar. Hosting-CI bleibt für Verträge zuständig, der eigene Ubuntu-Agent für reale CPU-ASR. Pi5 sowie physische Desktop-/Mikrofonprüfungen bleiben eigene Abnahmen.

### M2 — Residenten ASR-Pfad für Ubuntu auswählen: 🟡 Freigabeblocker

Issues: [#36](https://github.com/geisten/geist-diktat/issues/36), [#37](https://github.com/geisten/geist-diktat/issues/37), [#34](https://github.com/geisten/geist-diktat/issues/34).

- [x] Geist und quantisiertes Whisper auf identischem deutschen Pilot verglichen.
- [ ] Zuerst residenten whisper.cpp-Kontext für das Ubuntu-Desktopprofil im eigenen Adapter entwickeln: einmal laden, kontinuierlich Audio übernehmen, begrenzte Arbeitspuffer, geordneter Stop. Geist hält sein Modell bereits während einer Sitzung; dort segmentweisen Decode-Stillstand und Lesepfad untersuchen.
- [ ] Additiven Ereignismodus mit `session_id`, Audiozeit, `partial`, `final`, `state`, `error` definieren; v1-Zeilenausgabe kompatibel lassen. Nur stabile Endergebnisse automatisch einfügen. Alte Sitzungen dürfen keinen Text nachliefern.
- [ ] VAD-Endpunkte, kürzere Fenster und begrenzte Überlappung einzeln vergleichen. Kontext-Neuberechnung kann mehr Zeit kosten; doppelte Wörter und verlorene Satzanfänge erhalten Regressionen.
- [ ] Ubuntu x64: residenten CPU-Pfad gegen faster-whisper INT8 vergleichen; den Standard anhand Qualität, Einfügelatenz, Speicher und Stabilität wählen. Den ersten Kandidaten mit bestandenen Toren produktisieren; eine vollständige Modellrangliste ist keine Release-Voraussetzung.
- [ ] Parakeet v3 und Qwen3-ASR als weitere Kandidaten prüfen, wenn die ersten Pfade die Tore verfehlen oder eine konkrete verbleibende Qualitätslücke besteht; vorher Sprach-/Runtime-/Speicherprüfung.
- [ ] 30/60 Minuten zeitgetreue Dateien **und physische Aufnahme** auf dem Ubuntu-Zielprofil mit dokumentierter Last und Geräteprofil. Das ist ein Belastungstest des Diktats, kein Versprechen einer eigenständigen Gesprächstranskriptionsfunktion.
- [ ] Die dokumentierte Prozessschnittstelle mit einem minimalen externen Referenzclient abnehmen: Audiozufuhr, finale Texte, Zustandsereignisse, Start/Stop und Fehler. Eigene Editor-/IBus-Adapter müssen denselben Vertrag nutzen.

**Technische Abnahmekriterien für das Ubuntu-Profil:** Durchsatz-RTF ≤0,8; p95 vom annotierten Sprachende bis zur Einfügung ≤3 s im Live-Test; kein wachsender Audio-Rückstand, kein stiller Frameverlust und kein Überlastabbruch im normalen 60-Minuten-Test. Überlast muss weiterhin kontrolliert abbrechen. Globaler Stop beendet Aufnahme und unterbindet weitere Einfügungen innerhalb 1 s. Das sind Anforderungen, keine erzielten Werte. Die bisherigen Pi5-Zielwerte werden im separaten Folgeprofil weitergeführt.

**Bei Nichtbestehen:** Der Ubuntu-Beta-Start wartet; Qualität und Zeitgewinn werden nicht für einen Termin abgeschwächt. Größere Puffer ersetzen das Tor nicht. Pi5 bleibt davon unabhängig experimentell. Lokale Verarbeitung bleibt Standard; kein stiller Cloud-Fallback.

### M3 — Deutsche Qualitätsabnahme und experimentelle DACH-Tests: 🟡

Issues: [#38](https://github.com/geisten/geist-diktat/issues/38), [#39](https://github.com/geisten/geist-diktat/issues/39).

- [x] Deutsche Lesesprache, simuliertes Rauschen, Schweizer Varianten und ein natürliches längeres Gespräch im Pilot untersucht.
- [ ] Rechtegeklärtes, menschlich referenziertes Set: spontane Diktate, Dialoge, Selbstkorrekturen, Namen, Zahlen, Negationen, Komposita und Code-Switching.
- [ ] DACH-Matrix mit regionaler Expertise festlegen: deutsche Regionalgruppen, österreichische und Schweizer Varianten. Startumfang mindestens fünf unabhängige Sprecher und 30 Minuten bewertbare Sprache je beanspruchter Gruppe; Standardsprache mindestens zwei Stunden/20 Sprecher. Das Mindestdesign garantiert noch keine statistische Repräsentativität.
- [ ] Sprecher, Ursprungsaufnahmen, parallele Inhalte und deren Rauschvarianten gemeinsam einem Split zuordnen. Entwicklungs- und versiegeltes Freigabeset trennen. Vorhandene Piloten nur zur Entwicklung verwenden.
- [ ] Headset, Laptop-/USB-Mikrofon, Entfernung, Raumhall, Tastatur, Lüfter und Hintergrundsprache tatsächlich aufnehmen; 20/10/5-dB-Simulationen ergänzend erhalten.
- [ ] RMS gegen Silero-VAD prüfen; Entrauschung anschließend separat als A/B-Versuch. Saubere Sprache und leise Satzanfänge dürfen nicht systematisch schlechter werden.
- [ ] WER mit festgelegter Normalisierung, CER, Namen-/Zahlen-/Negationsfehler, ungesprochene Wörter und Korrekturaufwand ausweisen. Für den Produktmodus die inhaltstreue Übertragung ins Standarddeutsche menschlich referenzieren und regional bewerten. Historische WER gegen Dialektschreibung bleibt eine gesonderte Forschungskennzahl; dafür wird kein zweiter Beta-Modus gebaut.

**Tor:** Sauberes Standarddeutsch ≤10 % WER, 10 dB ≤25 % auf dem unabhängigen Set; Sprecher-basierte Konfidenzintervalle und schlechteste Gruppen mitberichten. DACH-Ergebnisse werden pro Region mit Stichprobenumfang und Grenzen experimentell veröffentlicht und blockieren die Standarddeutsch-Beta nicht. Für eine spätere reguläre Dialektfreigabe bleibt ≤25 % normalisierte WER gegen die standarddeutsche Referenz ein vorgeschlagenes Entwicklungsziel; vor dieser Freigabe sind Machbarkeit und regionale Kriterien festzulegen. Keine stille Lockerung nach Einsicht in Freigabedaten. Mindestens eine Stunde Stille/Nichtsprachgeräusche ohne automatisch eingefügten Text; zusätzlich keine erfundenen Sätze in manuell geprüften Sprach-/Rauschfällen. Das ist kein Versprechen einer Halluzinationsrate von null im Alltag.

Bei Nichterreichen keine reguläre Freigabe der betroffenen Sprachgruppe; experimentelle Ergebnisse bleiben als solche sichtbar. Explizite Nutzerkorrekturen können später ein rechtegeklärtes Anpassungsset bilden; Fine-Tuning erst nach Fehleranalyse und mit getrenntem Nachweis auf ungesehenen Sprechern.

### M4 — Einbettung in echte Anwendungen: 🟡

Issues: #19, #20, #23, #24, #27–29, [#31](https://github.com/geisten/geist-diktat/issues/31), [#32](https://github.com/geisten/geist-diktat/issues/32), [#33](https://github.com/geisten/geist-diktat/issues/33), [#34](https://github.com/geisten/geist-diktat/issues/34), [#35](https://github.com/geisten/geist-diktat/issues/35).

- [x] Echte Vim-/Neovim-Prozesse, Unicode, 100 Wechsel, IBus-Lifecycle, GTK3-/Qt5-Felder und Schutzfeldregeln getestet.
- [ ] Die fünf verbindlichen Anwendungen auf dem Ubuntu-GNOME-Zielprofil abnehmen: Vim, Neovim, vorab festgelegter GNOME-Texteditor, Firefox, LibreOffice Writer. Jede Matrixzelle erhält OS-, Desktop-, Toolkit-/App-Version, Paketformat, Datum und Ergebnis.
- [ ] Für diese Anwendungen Cursor/Selektion, Modus/Buffer/Fokus, Undo, IME-Wechsel, Passwort/PIN, globalen Stop, Gerätewechsel, Sperren/Entsperren und Session-Neustart prüfen. Das tatsächlich verwendete Paketformat gehört zwingend zur jeweiligen Zelle, auch wenn es Flatpak oder Snap ist.
- [ ] Weitere Chromium-/Electron-/Qt-Anwendungen, Paketvarianten, Xorg und KDE separat mit Teststatus dokumentieren; deren vollständige Matrix ist kein Tor für diese Beta.
- [ ] Ubuntu bevorzugt IBus-Text-Commit; globalen Shortcut über verfügbares Portal integrieren. Fehlende Fähigkeiten im Doctor anzeigen. `wtype` bleibt eine bedingte Senke, keine universelle Wayland-Lösung.
- [ ] Bei nicht mehr sicher bestimmtem Einfügeziel keine automatische Einfügung; Wiederauffinden bereits erkannter Ergebnisse und verständliche Statusanzeige abnehmen. macOS-Feldtests liegen im Folgeprofil.

**Tor:** Alle zugesagten Zellen bestehen; geschützte/unklare Ziele erhalten keinen Text. Nicht unterstützte Pfade erkennbar deaktivieren. Globaler Stop wirkt auch während Decoder-Stillstand. Headless-CI allein schließt dieses Tor nicht.

### M5 — Erststart und Betrieb ohne Entwicklerwerkzeuge: 🟡

Issues: [#21](https://github.com/geisten/geist-diktat/issues/21), [#29](https://github.com/geisten/geist-diktat/issues/29), [#30](https://github.com/geisten/geist-diktat/issues/30), [#32](https://github.com/geisten/geist-diktat/issues/32).

- [x] Pakete, Editorinstallation, Diagnose, geprüfte Downloads und macOS-App-Prototyp vorhanden.
- [ ] Modellprofil vorschlagen; Downloadgröße, Fortschritt, Wiederaufnahme und Speichermangel verständlich behandeln. Mikrofon wählen, Pegel/echte Aufnahme prüfen, Testdiktat einfügen, Shortcut zuordnen.
- [ ] Ubuntu-Paketabhängigkeiten und Eingabequellenregistrierung auf frischen Systemen vollständig abnehmen. Eine selbstständig lauffähige macOS-App ist Aufgabe des Folgeprofils.
- [ ] Update, Rollback, abgebrochenes Setup, verbliebener Lock und Deinstallation über einen verständlichen Bedienpfad. Pakettexte an tatsächliche Architektur anpassen.
- [ ] Mindestens fünf externe Personen ohne Projektinterna auf frischen Ubuntu-Installationen bzw. frischen Benutzerprofilen beobachten; die Installationsprüfung muss auch die Abwesenheit vorhandener Entwicklerabhängigkeiten abdecken: Klicks, Berechtigungen, Downloadzeit, aktive Einrichtungszeit und Zeit bis zum ersten korrekt eingefügten Satz dokumentieren.

**Tor:** Alle fünf erreichen das Testdiktat ohne Terminal-Diagnose oder Entwicklerhilfe. Keine fehlenden Laufzeitabhängigkeiten; kaputter Download/Offline/Update lässt sich geführt beheben. Alltag: ein Shortcut. Erstinstallation: geführter Ablauf mit erforderlichen OS-Dialogen. Erst Messergebnisse rechtfertigen ein „One-Click“-Versprechen.

### M6 — Externen Nutzennachweis bestehen: ⬜ vor dem ersten öffentlichen Download

- [ ] Germar gewinnt mindestens fünf externe Pilottester aus seinem Umfeld. Das Projekt stellt [Pilotprotokoll](BETA-PILOT.md), Aufgaben, Messvorlage und Auswertung bereit. Die bestätigte Rekrutierungszusage ist noch kein Nachweis verfügbarer Teilnehmer.
- [ ] Vor dem Pilot Kohorte, Aufgabenpaare, Anwendungsversionen, Kandidaten-Build/Modell und Auswertungsregel einfrieren. Alltags- und technische Texte sind gleichberechtigte Pflichtkategorien.
- [ ] Personenbezogene Zeitgewinne bis zum fertig korrigierten Text auswerten: je Kategorie Median ≥25 % und mindestens vier von fünf Personen schneller als beim Tippen. Fehler, Abbrüche und fehlende Ergebnisse nicht aussortieren.
- [ ] Zusätzlich müssen alle fünf den geführten Erststart ohne Projekt-/Entwicklerhilfe bewältigen. Diagnosefähigkeit erfahrener Entwickler ist keine Voraussetzung für das Produkt.
- [ ] Bei Änderungen nach einem gescheiterten Pilot einen neuen Kandidaten mit neuen, vergleichbaren Aufgaben prüfen. Alte Fehlversuche und Versionswechsel nachvollziehbar erhalten.

**Tor:** Sowohl Nutzenkriterium als auch M1–M5 für das Ubuntu-Profil bestanden. Ergebnisse pro Person und Kategorie berichten; eine kleine Pilotgruppe rechtfertigt keine allgemeine Marktüberlegenheitsbehauptung. Der Mindestnutzen wird vor dem öffentlichen Download nachgewiesen, nicht erstmals in der öffentlichen Beta gesucht.

### M7 — Öffentliche Vorstellung und Beta-Download gemeinsam: ⬜

- [ ] Versionierte, signierte Release-Artefakte mit Modell-/Abhängigkeitslizenzen, Prüfsummen, Build-Provenienz und Wiederherstellung bereitstellen. Mit exakt ausgelieferten Binaries/Modellen die technischen Gates bestehen; Änderungen am Diktatpfad nach dem Pilot erfordern passende erneute Nutzentests.
- [ ] Supportmatrix nennt die fünf geprüften Anwendungen und deren konkrete Versionen/Paketformate. Weitere Apps, DACH-Varianten und Pi5 erhalten einen ehrlichen experimentellen bzw. ungeprüften Status.
- [ ] Demo, numerische Evidenz, Installationsanleitung und Beta-Download gemeinsam vorbereiten und veröffentlichen. Kein separater öffentlicher Vorab-Demo-Start als Ersatz für den funktionsfähigen Download.
- [ ] Aufmerksamkeit auf belegbaren Arbeitsvorteil und lokale Entwickler-/Editorintegration richten. Keine Behauptung universeller Linux-Unterstützung, genereller SOTA-Überlegenheit oder ungeprüfter One-Click-Installation.
- [ ] Offene P1 schließen, P2 für das Beta-Profil beurteilen und bekannte Einschränkungen dokumentieren. Öffentliche Beta-Rückmeldungen zu Abbrüchen, Einfügefehlern, Korrekturaufwand und Installation erfassen; Sprachinhalte nur nach ausdrücklicher Zustimmung.

**Freigabeentscheidung:** Kein festes Datum. Erst nach M0–M6 für das vereinbarte Ubuntu-Profil veröffentlichen. Dieser bestätigte Plan beauftragt die Planaktualisierung; ein Produktrelease oder Nachrichten an Tester werden dadurch nicht bereits ausgeführt.

## Folgeprofile außerhalb des ersten Beta-Startpfads

- **Pi5 (#36/#37):** small Q5_1 Beam 1 resident, danach mehrsprachiges base; Threads, Quantisierung, BLAS und Kühlung getrennt prüfen. Weiterhin RTF ≤0,8, p95 ≤3 s, 30/60-Minuten-Dauerabnahme; für 4 GiB als Entwicklungsziel Prozessbaum-RSS ≤1,5 GiB ohne fortschreitenden Swap-I/O/Drosselung. Bis zum Nachweis experimentell.
- **macOS (#32):** native Capture-/Gerätepfade, App-/TCC-Abnahme, gebündelte Abhängigkeiten, Developer-ID/Hardened Runtime/Notarisierung/Stapling und Gatekeeper-Prüfung. Fehlende Signieridentitäten blockieren diese Plattform, nicht die Ubuntu-Beta.
- **Weitere Linux-Profile (#31):** Xorg/KDE, zusätzliche Apps sowie zusätzliche Flatpak-/Snap-Varianten mit eigener Matrix qualifizieren.
- **Reguläre DACH-Unterstützung (#38/#39):** breite Tests weiterführen, unabhängige Sprecher und regionale Referenzen erweitern; erst nach eigener Abnahme das experimentelle Kennzeichen entfernen.
- **Weitere Entwicklerprodukte (#34):** C-SDK und Netzwerkdienst nur bei begründetem Bedarf später planen. Die erste Beta liefert den lokalen Prozessvertrag.
