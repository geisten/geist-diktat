# Produktfreigabe: Stand und Reihenfolge

Stand: **6. September 2026**. Implementierungsbasis: `5e27010c461a6cff4ba830af52bf78df94cc7213`, Branch `codex/product-readiness`. Dieser Plan ersetzt die Reihenfolge vom 5. September.

**Noch kein allgemeines Produktrelease.** Die Stabilitätsbasis steht. Die größten Blocker bleiben kontinuierliches Pi5-Diktat, Qualität unter Rauschen, breite DACH-Abdeckung sowie Desktop- und Erststart-Abnahme. Empfohlen ist eine gestufte Freigabe pro geprüftem Plattform-/Sprachprofil; das Ziel einer breiten DACH-Unterstützung bleibt bestehen.

✅ = implementiert und im genannten Umfang getestet; 🟡 = teilweise umgesetzt; ⬜ = offen. Umsetzung auf dem Branch bedeutet nicht Merge, Veröffentlichung oder Feldabnahme. Die GitHub-Issues #16–40 waren bei der heutigen Abfrage weiterhin offen.

Messungen: [Implementierungsbericht](IMPLEMENTATION-2026-09-06.md). Architekturentscheidung, Alternativen und aktuelle Primärquellen: [SOTA-Analyse](RELEASE-STRATEGY-2026-09-06.md).

## Bereits umgesetzt

| Status | Bereich / Issues | Nachgewiesene Umsetzung | Verbleibende Abnahme |
|---|---|---|---|
| ✅ | Core #16, #17, #25, #26, #40 | EOF/Teilframes, Fehlerstatus, UTF-8 über Token-Grenzen, RMS-Validierung, NEON/x86/Scalar-Auswahl | Regressionen bei Backendänderungen erhalten |
| ✅ | Installationssicherheit #21, #22 | Validiertes Staging, atomarer Austausch, Vorversion, Lock; vorhandene Engine-Checkouts erhalten | Komfortable Wiederherstellung unter M5 |
| ✅ | Aufnahmefehler #18 | Capture-/Decoder-Fehler sichtbar; eigene Prozessgruppen kontrolliert beendet | Physische Geräte-/Berechtigungsabnahme unter M4 |
| ✅ | Vim/Neovim #19, #20, #24, #27–29 | Asynchrone Adapter, UTF-8-Framing, Sitzungswechsel, begrenzte Ausgabequeue, native Paketinstallation | Breite interaktive Modus-/Fokusmatrix unter M4 |
| ✅ | IBus-Lifecycle #23 | Reaping, Stop/Neustart, EOF/HUP, 100 Wechsel | Weitere Desktop-Sitzungen unter M4 |
| ✅ | Pipeline #33 | Wörtliche zeilenweise UTF-8-Übergabe ohne Shell-Auswertung | Verfügbarkeit der Senke pro Desktop |
| ✅ | Tests / GitHub-Ubuntu-Agent | macOS und Pi-Ubuntu-Container je 77 Fälle; gehostetes Ubuntu x64/ARM64 je 77 Fälle; echter x64-ASR-Pilot | Kein Nachweis für GUI, physische Mikrofone oder Dauer-ASR |
| 🟡 | Supervisor / Pi5 #36, #37 | Capture entkoppelt, standardmäßig 6 s Queue, Überlast Exit 75; Whisper-/Beam-Vergleich | Kontinuierlicher Lesepfad und ausreichend schneller residenter Decoder fehlen |
| 🟡 | Sprache #38, #39 | 47 Pilot-Fixtures; WER-, Rausch-, Schweizer Dialekt- und Gesprächsmessungen; lokaler Gate-Checker | Unabhängiges DACH-Set und bestandene Qualitätsgates fehlen |
| 🟡 | Vertrag / Status #34, #35 | PCM16/UTF-8/Exitcode-Vertrag v1; IBus-Fokus-/Schutzfeldregeln | Zustandsereignisse, Teil-/Endergebnisse und globale Stop-Abnahme |
| 🟡 | Ubuntu-Apps #31 | Echte IBus-/GTK3-/Qt5-Prüfungen unter privatem D-Bus/Xvfb | GNOME Wayland/Xorg, KDE, moderne Toolkits und Sandbox-Apps |
| 🟡 | Erststart #30 | Doctor, SHA-geprüfte Modelldownloads, Setup, Editorinstallation | Mikrofonwahl, Fortschritt/Wiederaufnahme, Recovery, Nutzertests |
| 🟡 | macOS #32 | Swift-Menüleisten-App, Hotkey, Vorschau/Kopieren, optionales AX-Einfügen; Build/ad-hoc-Signatur grün | Native Capture-/Abhängigkeitslösung, GUI/TCC, Developer-ID/Notarisierung |

Der [GitHub-Lauf 34020085582](https://github.com/geisten/geist-diktat/actions/runs/34020085582) ist auf genau diesem Implementierungsstand vollständig grün. Ubuntu-Core-Coverage: **98,08 % Zeilen, 73,50 % Zweige, 100 % Funktionen**, mit kontrollierter Engine. Das erfasst keine Modell-, Treiber- oder vollständige Produktabdeckung.

**Der Workflow misst WER, ruft `check_gates.py` aber bislang nicht auf.** Ein grüner Lauf bedeutet deshalb noch keine bestandene Qualitätsfreigabe.

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

M1 und die Datenbeschaffung für M3 können sofort beginnen. M2 braucht die Messinstrumentierung; M4 den stabilen Ereignisvertrag aus M2. M5 baut auf den geprüften Aufnahme-/Einfügepfaden auf. M6 prüft die konkreten Release-Artefakte. Fortschritt wird an Ergebnissen gemessen; belastbare Termine erfordern zuerst den Backend-Prototyp und verfügbare Sprecher.

### M0 — Stabilitätsbasis sichern: ✅ umgesetzt, Integration noch offen

- [x] Korrekturen, Adapter, Installer und Tests implementiert und gepusht.
- [x] GitHub-Ubuntu x64/ARM64 und manuellen CPU-Agent-Lauf erfolgreich ausgeführt.
- [ ] Änderungen reviewen und in den vorgesehenen Release-Branch integrieren. Issues erst nach passender Abnahme schließen; noch keinen Release-Tag setzen.

Evidenz: [Implementierungsbericht](IMPLEMENTATION-2026-09-06.md), [CI-Lauf](https://github.com/geisten/geist-diktat/actions/runs/34020085582).

### M1 — Freigabe messbar machen: 🟡 höchste nächste Priorität

Issues: [#34](https://github.com/geisten/geist-diktat/issues/34), [#36](https://github.com/geisten/geist-diktat/issues/36), [#38](https://github.com/geisten/geist-diktat/issues/38).

- [x] Pilotmanifest, numerische Reports, gepinnte Modelle/Engines, Gate-Checker vorhanden.
- [ ] Gesonderten Release-Qualitätsjob mit sauberer Sprache **und** Rauschen anlegen; Checker verpflichtend ausführen. Fehlende Gruppen/Referenzen oder fehlgeschlagene Clips verhindern die Freigabe.
- [ ] Modell, Build, Hardware, Decoderparameter und Korpusrevision pro Plattform speichern. Numerische Release-Evidenz dauerhaft archivieren; bisherige Actions-Aufbewahrung: 30 Tage.
- [ ] Zeitpunkte für Audioblock, Sprachende, Decoderstart/-ende, stabiles Ergebnis und tatsächliche Einfügung erfassen. Modellladen, Encoder, Decoder und Warteschlangen separat messen; kalte und warme Starts trennen.
- [ ] Live-Harness zählt empfangene/verarbeitete/als verworfen gemeldete Frames, maximalen Lesestillstand, Queue-Alter/-Tiefe, Stop-Zeit und Prozessbaum-RSS. Auch Betriebssystem-Pipes berücksichtigen.

**Tor:** Ein absichtlich schlechter oder unvollständiger Report blockiert den Release-Job. Latenz ist bis zur Texteingabe messbar. Hosting-CI bleibt für Verträge zuständig, der eigene Ubuntu-Agent für reale CPU-ASR. Pi5 sowie physische Desktop-/Mikrofonprüfungen bleiben eigene Abnahmen.

### M2 — Residenten ASR-Pfad und Plattformprofile auswählen: 🟡 Freigabeblocker

Issues: [#36](https://github.com/geisten/geist-diktat/issues/36), [#37](https://github.com/geisten/geist-diktat/issues/37), [#34](https://github.com/geisten/geist-diktat/issues/34).

- [x] Geist und quantisiertes Whisper auf identischem deutschen Pilot verglichen.
- [ ] Zuerst residenten whisper.cpp-Kontext im eigenen Adapter entwickeln: einmal laden, kontinuierlich Audio übernehmen, begrenzte Arbeitspuffer, geordneter Stop. Geist hält sein Modell bereits während einer Sitzung; dort segmentweisen Decode-Stillstand und Lesepfad untersuchen.
- [ ] Additiven Ereignismodus mit `session_id`, Audiozeit, `partial`, `final`, `state`, `error` definieren; v1-Zeilenausgabe kompatibel lassen. Nur stabile Endergebnisse automatisch einfügen. Alte Sitzungen dürfen keinen Text nachliefern.
- [ ] VAD-Endpunkte, kürzere Fenster und begrenzte Überlappung einzeln vergleichen. Kontext-Neuberechnung kann mehr Zeit kosten; doppelte Wörter und verlorene Satzanfänge erhalten Regressionen.
- [ ] Pi5: small Q5_1 Beam 1 resident, anschließend mehrsprachiges base als kleineren Kandidaten vergleichen; 1/2/3/4 Threads, Quantisierung und BLAS getrennt messen. Keine englischen `.en`-Modelle für Deutsch einsetzen.
- [ ] Mac: Whisper mit Metal, optional Core-ML-Encoder vergleichen. Ubuntu x64: residenten CPU-Pfad gegen faster-whisper INT8. Parakeet v3 und Qwen3-ASR nach Sprach-/Runtime-/Speicherprüfung als Herausforderer aufnehmen; Details in der SOTA-Analyse.
- [ ] Anschließend 30/60 Minuten zeitgetreue Dateien **und physische Aufnahme** pro beanspruchter Plattform mit dokumentierter Kühlung, Last und Geräteprofil.

**Vorgeschlagene Produktziele:** Durchsatz-RTF ≤0,8; p95 vom annotierten Sprachende bis zur Einfügung ≤3 s im Live-Test; kein wachsender Audio-Rückstand, kein stiller Frameverlust und kein Überlastabbruch im normalen 60-Minuten-Test. Überlast muss weiterhin kontrolliert abbrechen. Globaler Stop beendet Aufnahme und unterbindet weitere Einfügungen innerhalb 1 s. Pi5/4 GiB: Prozessbaum-RSS als Ziel ≤1,5 GiB, kein fortschreitender Swap-I/O und keine Drosselung im freigegebenen Kühlprofil. Das sind zu validierende Anforderungen, keine erzielten Werte.

**Bei Nichtbestehen:** Pi5 bleibt experimentell; eine bestandene Desktop-Konfiguration kann separat in die Beta. Größere Puffer oder Übertakten ersetzen das Tor nicht. Beschleuniger-Hardware erst nach belegter Modell-/Operatorunterstützung als eigenes Profil planen. Lokale Verarbeitung bleibt Standard; kein stiller Cloud-Fallback.

### M3 — Deutsche Qualität und breite DACH-Abdeckung: 🟡 Beschaffung sofort starten

Issues: [#38](https://github.com/geisten/geist-diktat/issues/38), [#39](https://github.com/geisten/geist-diktat/issues/39).

- [x] Deutsche Lesesprache, simuliertes Rauschen, Schweizer Varianten und ein natürliches längeres Gespräch im Pilot untersucht.
- [ ] Rechtegeklärtes, menschlich referenziertes Set: spontane Diktate, Dialoge, Selbstkorrekturen, Namen, Zahlen, Negationen, Komposita und Code-Switching.
- [ ] DACH-Matrix mit regionaler Expertise festlegen: deutsche Regionalgruppen, österreichische und Schweizer Varianten. Startumfang mindestens fünf unabhängige Sprecher und 30 Minuten bewertbare Sprache je beanspruchter Gruppe; Standardsprache mindestens zwei Stunden/20 Sprecher. Das Mindestdesign garantiert noch keine statistische Repräsentativität.
- [ ] Sprecher, Ursprungsaufnahmen, parallele Inhalte und deren Rauschvarianten gemeinsam einem Split zuordnen. Entwicklungs- und versiegeltes Freigabeset trennen. Vorhandene Piloten nur zur Entwicklung verwenden.
- [ ] Headset, Laptop-/USB-Mikrofon, Entfernung, Raumhall, Tastatur, Lüfter und Hintergrundsprache tatsächlich aufnehmen; 20/10/5-dB-Simulationen ergänzend erhalten.
- [ ] RMS gegen Silero-VAD prüfen; Entrauschung anschließend separat als A/B-Versuch. Saubere Sprache und leise Satzanfänge dürfen nicht systematisch schlechter werden.
- [ ] WER mit festgelegter Normalisierung, CER, Namen-/Zahlen-/Negationsfehler, ungesprochene Wörter und Korrekturaufwand ausweisen. Dialektschreibung und Übertragung ins Hochdeutsche getrennt referenzieren und bewerten.

**Tor:** Sauberes Standarddeutsch ≤10 % WER, 10 dB ≤25 % auf dem unabhängigen Set; Sprecher-basierte Konfidenzintervalle und schlechteste Gruppen mitberichten. Als vorgeschlagenes DACH-Ziel ≤25 % normalisierte WER pro beanspruchter Dialektgruppe und Referenzaufgabe vorab festschreiben; Machbarkeit zunächst am Entwicklungsset prüfen. Keine stille Lockerung nach Einsicht in Freigabedaten. Mindestens eine Stunde Stille/Nichtsprachgeräusche ohne automatisch eingefügten Text; zusätzlich keine erfundenen Sätze in manuell geprüften Sprach-/Rauschfällen. Das ist kein Versprechen einer Halluzinationsrate von null im Alltag.

Bei Nichterreichen keine Freigabe der betroffenen Sprachgruppe. Explizite Nutzerkorrekturen können später ein rechtegeklärtes Anpassungsset bilden; Fine-Tuning erst nach Fehleranalyse und mit getrenntem Nachweis auf ungesehenen Sprechern.

### M4 — Einbettung in echte Anwendungen: 🟡

Issues: #19, #20, #23, #24, #27–29, [#31](https://github.com/geisten/geist-diktat/issues/31), [#32](https://github.com/geisten/geist-diktat/issues/32), [#33](https://github.com/geisten/geist-diktat/issues/33), [#34](https://github.com/geisten/geist-diktat/issues/34), [#35](https://github.com/geisten/geist-diktat/issues/35).

- [x] Echte Vim-/Neovim-Prozesse, Unicode, 100 Wechsel, IBus-Lifecycle, GTK3-/Qt5-Felder und Schutzfeldregeln getestet.
- [ ] Zuerst Vim/Neovim und Ubuntu 24.04 GNOME Wayland vollständig abnehmen; anschließend Xorg und KDE separat. Jede Matrixzelle erhält OS-, Desktop-, Toolkit-/App-Version, Datum und Ergebnis.
- [ ] GTK3/4, Qt5/6, Firefox/Chromium, Electron, LibreOffice, Flatpak/Snap: Cursor/Selektion, Modus/Buffer/Fokus, Undo, IME-Wechsel, Passwort/PIN, globaler Stop, Gerätewechsel, Sperren/Entsperren und Session-Neustart prüfen.
- [ ] Ubuntu bevorzugt IBus-Text-Commit; globalen Shortcut über verfügbares Portal integrieren. Fehlende Fähigkeiten im Doctor anzeigen. `wtype` bleibt eine bedingte Senke, keine universelle Wayland-Lösung.
- [ ] macOS: native Audioaufnahme und Gerätewechsel ergänzen; festgehaltenes Einfügeziel, Secure Input und Berechtigungswiderruf in TextEdit, Browsern, Terminal und Editoren tatsächlich testen. Nicht einfügbaren Text in Vorschau erhalten.

**Tor:** Alle zugesagten Zellen bestehen; geschützte/unklare Ziele erhalten keinen Text. Nicht unterstützte Pfade erkennbar deaktivieren. Globaler Stop wirkt auch während Decoder-Stillstand. Headless-CI allein schließt dieses Tor nicht.

### M5 — Erststart und Betrieb ohne Entwicklerwerkzeuge: 🟡

Issues: [#21](https://github.com/geisten/geist-diktat/issues/21), [#29](https://github.com/geisten/geist-diktat/issues/29), [#30](https://github.com/geisten/geist-diktat/issues/30), [#32](https://github.com/geisten/geist-diktat/issues/32).

- [x] Pakete, Editorinstallation, Diagnose, geprüfte Downloads und macOS-App-Prototyp vorhanden.
- [ ] Modellprofil vorschlagen; Downloadgröße, Fortschritt, Wiederaufnahme und Speichermangel verständlich behandeln. Mikrofon wählen, Pegel/echte Aufnahme prüfen, Testdiktat einfügen, Shortcut zuordnen.
- [ ] Abhängigkeiten vollständig liefern: macOS ohne Homebrew/externes Python/SoX starten können; native Capture-Lösung bzw. mitgelieferte Runtime prüfen. Ubuntu-Paketabhängigkeiten und Eingabequellenregistrierung abnehmen.
- [ ] Update, Rollback, abgebrochenes Setup, verbliebener Lock und Deinstallation über einen verständlichen Bedienpfad. Pakettexte an tatsächliche Architektur anpassen.
- [ ] Fünf Personen ohne Entwicklerkontext je freizugebender Desktop-Plattform auf frischen Systemen beobachten: Klicks, Berechtigungen, Downloadzeit, aktive Einrichtungszeit und Zeit bis zum ersten korrekt eingefügten Satz dokumentieren.

**Tor:** Alle fünf erreichen das Testdiktat ohne Terminal-Diagnose oder Entwicklerhilfe. Keine fehlenden Laufzeitabhängigkeiten; kaputter Download/Offline/Update lässt sich geführt beheben. Alltag: ein Shortcut. Erstinstallation: geführter Ablauf mit erforderlichen OS-Dialogen. Erst Messergebnisse rechtfertigen ein „One-Click“-Versprechen.

### M6 — Release-Kandidat und gestufte Beta: ⬜

- [ ] M1–M5 für jedes veröffentlichte Profil bestehen; DACH-/Pi5-/App-Claims nur für jeweils abgenommene Gruppen. Experimentelle Profile klar kennzeichnen.
- [ ] macOS Developer-ID/Hardened Runtime/Notarisierung/Stapling und Gatekeeper-Test auf frischem System. Beim letzten lokalen Check gab es keine gültigen Codesigning-Identitäten; deren Bereitstellung bleibt externer Meilenstein.
- [ ] Versionierte signierte Artefakte, Prüfsummen, Modell-/Abhängigkeitslizenzen, Build-Provenienz und Rückkehr zur Vorversion bereitstellen.
- [ ] Gates mit exakt ausgelieferten Binaries/Modellen wiederholen; Supportmatrix, Grenzen und numerische Evidenz dauerhaft veröffentlichen.
- [ ] Begrenzte Alltagsbeta: Abbrüche, falsche Einfügeziele, Korrekturaufwand und erfolgreiche Sitzungen auswerten; Sprachinhalte nur nach ausdrücklicher Zustimmung erfassen. Offene P1 schließen, verbleibende P2 pro freigegebenem Profil bewerten und dokumentieren.

**Freigabeumfang:** Zuerst bestandene Editor-/Ubuntu-/Mac-Profile, Pi5 und weitere Dialekt-/Desktopprofile nach eigenen Toren. Eine allgemeine Freigabe für den gesamten ursprünglichen Anspruch folgt erst nach allen zugehörigen Abnahmen. Belegter Mehrwert heute: lokale Verarbeitung und gezielte Editor-/IBus-Komposition. Zielmehrwert: zuverlässiges tägliches Diktat mit geringem Korrekturaufwand und transparenter Kontrolle. Eine generelle SOTA-Erkennungsüberlegenheit oder bessere Bedienbarkeit gegenüber etablierten Produkten ist noch nicht nachgewiesen.
