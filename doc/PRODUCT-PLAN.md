# Reihenfolge bis zum alltagstauglichen Produkt

Stand: 5. September 2026. Dies ist ein umsetzbarer Arbeitsplan mit Abnahmetoren,
keine Zusage einer bereits vorhandenen Produktreife. Issues sind echte Aufgaben
im Repository. Die Messwerte und ihre Grenzen stehen im ergänzenden Qualitätsbericht.

## 1. Datenverlust und falschen Erfolg beseitigen — Freigabeblocker

Zuerst [EOF/Teilframes #16](https://github.com/geisten/geist-diktat/issues/16),
[Engine-Fehlerstatus #17](https://github.com/geisten/geist-diktat/issues/17) und
[Capture-Fehlerstatus #18](https://github.com/geisten/geist-diktat/issues/18).
Für den Ubuntu-x64-Pfad zusätzlich die [Backend-Auswahl #40](https://github.com/geisten/geist-diktat/issues/40) korrigieren. Parallel fachlich unabhängig: [atomarer Installer #21](https://github.com/geisten/geist-diktat/issues/21)
und [sichere Engine-Migration #22](https://github.com/geisten/geist-diktat/issues/22).
Unicode und Eingabegrenzen [#25](https://github.com/geisten/geist-diktat/issues/25)/
[#26](https://github.com/geisten/geist-diktat/issues/26) gehören in dieselbe Stabilitätsphase.

**Abnahme:** vorhandene Regressionsfälle auf macOS, Pi5 und Ubuntu x64/ARM64
bestehen, keine erwarteten Fehler verstecken; Abbruch/Offline/defektes Archiv
lassen die Vorversion nutzbar. Ein Recorderfehler zeigt einen Fehler statt „listening“.
Erst danach weitere automatische Texteinspeisung freigeben.

## 2. Deutsche Transkriptionsqualität belastbar machen

[Qualitätskorpus #38](https://github.com/geisten/geist-diktat/issues/38) und
[ungesprochener Text unter Rauschen #39](https://github.com/geisten/geist-diktat/issues/39)
haben Produktpriorität vor einer hübscheren Installation. Die aktuellen Pilot-WERs
reichen für die Behauptung „zuverlässiges deutsches Alltagsdiktat“ noch nicht.

Den Pilot um spontane Alltagssprache, Namen, Zahlen, Komposita, Code-Switching,
österreichische und deutsche Regionaldialekte, verschiedene Mikrofone und echte
Umgebungsgeräusche erweitern. Mindestens mehrere unabhängige Sprecher pro Variante;
Testdaten fest einfrieren und von Optimierungsdaten trennen. Nutzungsrechte zuerst
klären; menschliche Referenzen nicht durch Modell-Outputs ersetzen.

**Abnahme:** vorher vereinbarte und auf einem unabhängigen Testset gemessene WER-
und Halluzinationsgrenzen. Als zu validierende Produktziele: sauberes Hochdeutsch
≤10 % WER, 10-dB-Rauschbedingung ≤25 %, keine unmarkierten langen erfundenen Antworten
im festgelegten Negativtestset. Das sind Zielwerte, keine erreichten Ergebnisse
oder allgemeingültigen Branchenstandards. Dialekt-ASR und Übersetzung ins
Hochdeutsche separat bewerten. Auf demselben Korpus mindestens whisper.cpp als
Vergleich ausführen, bevor Überlegenheitsbehauptungen entstehen.

## 3. Pi5 für kontinuierliche Nutzung qualifizieren

[Pi5-Optimierung #36](https://github.com/geisten/geist-diktat/issues/36) und
[Capture/Decoder-Entkopplung #37](https://github.com/geisten/geist-diktat/issues/37).
Zuerst Profiling und reproduzierbare Messungen, danach jeweils nur einen Parameter
ändern. Vier Threads sind schneller als ein Thread; ein niedrigerer WER einzelner
Zwei-Thread-Läufe ist noch keine stabile Optimierung. Der Streaming-Worker läuft
über `audio_begin` bereits; ein zusätzliches `GEIST_AUDIO_STREAM=1` ist kein
belegter Turbo.

**Abnahme:** 30- und 60-minütige reale Gespräche und Diktate mit physischer Aufnahme,
kein stiller Frameverlust, kein wachsender Rückstand, begrenzte Puffer, kontrollierter
Überlastzustand und verlässlicher Stop. Vorgeschlagene Latenzziele: p95 ≤3 s nach
Äußerungsende, Durchsatz-RTF ≤0,8 als Reserve. RSS/Swap und Temperatur kontinuierlich
messen; die 4-GiB-Variante getrennt freigeben. Falls der Modellpfad das nicht erreicht,
kleineres Modell bzw. anderen ASR-Backend vergleichen statt nur Threadzahlen zu drehen.

## 4. Einen zuverlässigen Editor-Pfad fertigstellen

Neovim zuerst: [Framing #19](https://github.com/geisten/geist-diktat/issues/19),
[Sitzungsrennen #20](https://github.com/geisten/geist-diktat/issues/20),
[Queue/Fehler #24](https://github.com/geisten/geist-diktat/issues/24),
[plattformfähiger Standardstart #27](https://github.com/geisten/geist-diktat/issues/27).
Anschließend [Vim-Adapter #28](https://github.com/geisten/geist-diktat/issues/28)
und [Plugin-Installation #29](https://github.com/geisten/geist-diktat/issues/29).

**Abnahme:** Installation in leerem HOME, ein dokumentierter Shortcut, echte
zeitlich fragmentierte UTF-8-Ausgabe, 100 Toggle-Zyklen, Modus-/Buffer-/Fokuswechsel,
Undo und Fehleranzeige. Keine diktierte Zeichenfolge darf im Vim-Normalmodus als
Editorbefehl ausgeführt werden. Einen laufenden Audio-Prozess nicht mit blockierendem
`:read !…` integrieren.

## 5. Ubuntu-Desktop als erste systemweite Plattform abschließen

[IBus-Lifecycle #23](https://github.com/geisten/geist-diktat/issues/23),
[Desktop-/App-Matrix #31](https://github.com/geisten/geist-diktat/issues/31),
[Pipeline-Beispiele #33](https://github.com/geisten/geist-diktat/issues/33),
[Einbettungsvertrag #34](https://github.com/geisten/geist-diktat/issues/34) und
[Hörstatus/Fokusregeln #35](https://github.com/geisten/geist-diktat/issues/35).
GTK3/Qt5 unter Xvfb sind bereits geprüft. Daraus folgt keine Freigabe für
GNOME Wayland, KDE oder sandboxierte Anwendungen.

**Abnahme:** explizite Matrix für GNOME Wayland/Xorg, KDE, GTK3/4, Qt5/6,
Firefox/Chromium, Electron, LibreOffice und Flatpak/Snap. Globaler Shortcut,
Input-Source-Registrierung, geschützte Felder, Gerätewechsel und Session-Neustart
funktionieren oder werden als nicht unterstützt erkennbar angezeigt. Der private
CI-D-Bus darf nie die laufende Desktop-Sitzung eines Runners ersetzen.

## 6. Erst dann den One-Click-Erststart fertigstellen

[Setup/Doctor #30](https://github.com/geisten/geist-diktat/issues/30) bündelt die
vorher stabilisierten Teile: passende Installation, überprüfte Modell-Dateien,
Downloadfortschritt/Wiederaufnahme, Mikrofonwahl, Eingabequelle, Editorpfade,
konkrete Fehlerhilfe und ein sichtbares Testdiktat.

**Abnahme:** fünf Personen ohne Entwicklerkontext erreichen auf frisch vorbereiteten
Systemen ohne Terminal-Diagnose ihren ersten korrekt eingefügten Satz. Anzahl
Klicks, nötige Berechtigungsdialoge und Zeit bis zum ersten Diktat dokumentieren.
Betriebssystem-Berechtigungen ehrlich als notwendige Schritte ausweisen.
„Ein Shortcut im täglichen Betrieb“ und „One-Click-Installation“ bleiben zwei
verschiedene messbare Versprechen. Update/Rollback/Deinstallation gehören dazu.

## 7. macOS-Systemintegration und kontrollierte Beta

[macOS-Integration #32](https://github.com/geisten/geist-diktat/issues/32) baut auf
stabiler Prozessschnittstelle und Qualitätsprüfung auf: Hotkey, Mikrofonstatus,
geführte Berechtigungen, signierte/notarisierte Auslieferung, TextEdit/Browser/
Terminal-Tests und explizite Regeln für Secure Input. CLI-Support allein erfüllt
diese Aufgabe nicht.

Beta erst nach bestandenen Toren 1–6 auf den freigegebenen Linux-Umgebungen und
entsprechenden macOS-Toren. Release-Notes enthalten unterstützte Apps, bekannte
Grenzen und die gemessenen Qualitätswerte. Der heutige belastbare Mehrwert ist
die lokale, komponierbare C-/Prozessarchitektur mit gezielter Editor-/IBus-Anbindung.
Bessere Erkennung, weniger RAM oder einfacher Erststart gegenüber etablierten
Produkten sind aktuell nicht nachgewiesen.
