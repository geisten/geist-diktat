# Installierte Modellprofile

Stand: 7. September 2026. Die Integration auf `codex/product-readiness` ergänzt
Launcher, Setup, Doctor und Paketbau um den ausgewählten Entwicklungskandidaten
**Whisper small Q5_1, Beam 5, vier CPU-Threads**. Geist bleibt das Standardprofil
des bisherigen Build-/Releasewegs. Ein ausdrücklich mit `whisper-small` gebautes
Paket verwendet diesen Kandidaten als Paketvorgabe. Ein Produktrelease ist damit
nicht freigegeben.

## Bedienung

Nach Installation des passenden Pakets:

```sh
geist-diktat profile list
geist-diktat profile use whisper-small
geist-diktat setup
geist-diktat doctor --verify
geist-diktat run
```

`run` startet das Mikrofon. `profile use` speichert die Wahl atomar pro Benutzer
unter `$XDG_CONFIG_HOME/geist-diktat/profile.json`, standardmäßig
`~/.config/geist-diktat/profile.json`. Ein fehlender Decoder verhindert die
Auswahl. Das Modell kann anschließend mit `setup` geladen werden. Bestehende
Vim-/Neovim-/IBus-Aufrufe von `geist-diktat run` verwenden diese Wahl beim nächsten
Start; die Plugins benötigen keine eigenen Modellpfade.

Die Reihenfolge ist: `--profile NAME` vor dem Unterbefehl, dann
`GEIST_DIKTAT_PROFILE`, gespeicherte Benutzerwahl, Paketvorgabe und schließlich
Geist für alte Installationen. Eine ungültige Konfiguration ist ein sichtbarer
Fehler. Beispiel einer einmaligen Diagnose:

```sh
geist-diktat --profile whisper-small doctor --verify --json
```

`OMP_NUM_THREADS` und `GEIST_WHISPER_BEAM_SIZE` bleiben ausdrückliche
Entwicklerüberschreibungen; Doctor berichtet die wirksamen Werte. Modell- und
Decoderpfad können wie bisher per Umgebung überschrieben werden. Bei
`doctor --verify` muss ein überschriebenes Binary dennoch zur Prüfsumme im
Paket passen. Der geprüfte Kandidat verwendet vier Threads und Beam 5.

## Modellhaltung und Pi-Experimente

Das Whisper-Profil startet Capture erst nach bestätigter Modellbereitschaft.
Abgeschlossene Diktate verwenden denselben Worker; nach 60 Sekunden Leerlauf
wird dessen Speicher freigegeben. `worker start`, `worker status` und
`worker stop` erlauben Vorladen, Diagnose und ausdrückliche Freigabe.
[Stop-Regeln und Grenzen](WORKER-PI5.md).

Doctor berichtet auch `GEIST_DIKTAT_REUSE_MODEL`, `GEIST_DIKTAT_IDLE_SECONDS`,
`OMP_WAIT_POLICY`, `GEIST_WHISPER_AUDIO_CONTEXT=full|adaptive`,
`GEIST_WHISPER_CHUNK_SECONDS=4..28` und
`GEIST_WHISPER_TEMPERATURE_FALLBACK=0|1`. Standard bleiben voller Audiokontext,
28 Sekunden, Temperatur-Wiederholungen und Beam 5. Ungültige Werte scheitern
vor der Aufnahme. Nach Änderungen an Modell oder Decoderparametern den alten
Worker stoppen. Die experimentellen Pi-Parameter sind keine Freigabevorgabe.

## Setup und Fehlerbehandlung

Whisper lädt ausschließlich `ggml-small-q5_1.bin`; Gemma-Modell, Audio-Tower und
Mel-Konstanten sind für dieses Profil nicht erforderlich. Der erwartete SHA-256
ist `ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb`.
Ein korrekter Cache funktioniert ohne Download. Neue Dateien werden zunächst
als profilabhängige `.part`-Datei geschrieben, geprüft und erst danach atomar an
den Zielpfad verschoben. Ein fehlgeschlagener Download oder eine falsche
Prüfsumme ersetzt keine bisher vorhandene Modelldatei.

Bei den URL-Downloads kann ein erneutes `setup` einen unterbrochenen Download
mit curl fortsetzen, sofern der Server Range-Anfragen unterstützt. curl zeigt
den Transferfortschritt. Die Tower-Beschaffung des Geist-Profils verwendet
weiter den vorhandenen Fetcher; dieselbe Wiederaufnahme wird dafür nicht
behauptet. Ein Betriebssystem-Lock verhindert konkurrierende Setup-Prozesse und
wird beim Prozessende freigegeben. Symlinks auf Lock-/Teil-Dateien werden
zurückgewiesen. Ein vollständiger geführter Recovery-Dialog steht noch aus.

Doctor prüft ausgewählte Dateien, Decoder, Capture-Werkzeug und Profilkonsistenz.
`--verify` prüft zusätzlich Modell- und paketierte Decoder-Prüfsummen.
`ready=true` bedeutet bestandene Dateisystem-/Werkzeugprüfungen; es bestätigt
weder Mikrofonberechtigungen noch korrektes Einfügen in die fokussierte Anwendung.

## Pakete und Grenzen

Entwickler bauen gezielt:

```sh
sh scripts/build-whisper.sh
# Ubuntu, zusätzlich das IBus-Binary bauen:
make CC=gcc-14 ibus-engine-geist-diktat
GEIST_PACKAGE_PROFILE=whisper-small sh packaging/build-deb.sh
# macOS ARM64:
GEIST_PACKAGE_PROFILE=whisper-small sh packaging/build-tarball.sh
```

Das Paket enthält nur das gewählte Decoderprofil, Laufzeit-/Editoradapter,
Paketvorgabe, Modellhashes, Decoderhash nach Strip und den upstream MIT-Lizenztext.
Die Debian-Abhängigkeiten werden aus den tatsächlichen Decoder-/IBus-ELF-Dateien
mit `dpkg-shlibdeps` einschließlich erforderlicher ABI-Versionen abgeleitet.
Der vollständige MIT-Text steht zusätzlich in Debians `copyright`, damit er
auch bei Minimalinstallationen mit ausgeschlossener Dokumentation erhalten bleibt.

**Der Whisper-Build ist für den Build-Rechner optimiert.** Die offene
Distributionsabnahme ist in [#48](https://github.com/geisten/geist-diktat/issues/48)
erfasst. Die Metadaten nennen
ihn ausdrücklich einen Entwicklungsbuild ohne zugesagte breite CPU-Kompatibilität.
Die CI-Pakete sind Testartefakte, keine öffentlichen Beta-Releases. Die strenge
Linux-Tarballprüfung verlangt weiterhin einen statischen musl-Build; ein normaler
nativer glibc-Whisper-Build besteht diese Prüfung nicht. Der macOS-Tarball prüft
Systembibliotheken, ersetzt aber weder eine eigenständige App noch
Developer-ID-Signatur, Notarisierung oder eine eingefrorene OS-Supportmatrix.

## Testumfang

23 Launcher-/Profiltests prüfen unter anderem persistente Auswahl, fehlende
Decoder, ungültige Einstellungen, profilabhängige Ressourcen, Prüfsummen,
Downloadabbruch/Wiederaufnahme, konkurrierendes Setup und atomare Fehlerpfade.
Das sind kontrollierte Regressionen, keine Netzwerk- oder Mikrofonabnahme.

`quality-audit` mit `run_packages=true` baut auf Ubuntu 24.04 x64 und ARM64
je ein echtes `.deb` und installiert es in einem frischen Ubuntu-Container ohne
Compiler, CMake oder Git. Dort müssen Profilwahl, Diagnose mit ausschließlich
fehlendem Modell und das Laden des Decoders bis zum erwarteten Modellfehler
funktionieren. Diese Prüfung benötigt weder Audiodaten noch ein Audiogerät.

Mit `run_resident=true` prüft der eigene Ubuntu-Agent zusätzlich den installierten
Launcherpfad mit echtem gepinntem Modell und einer zeitgetreu zugespielten deutschen
Aufnahme. `benchmarks/package_smoke.py` führt Auswahl, Cache-Setup, Doctor mit
Hashprüfung und Erkennung in isolierten Benutzerverzeichnissen aus. Derselbe
Test lässt sich mit dem entpackten macOS-Tarball ausführen. Ein fehlerfrei
erkannter bekannter Clip ist ein Integrationstest, keine neue allgemeine WER.

## Nachgewiesener Stand

Laufzeit/Pakete `fd01781`, abschließende CI-Prüfung `e9aeed9`: 134 lokale Tests
auf macOS und jeweils 134 auf Ubuntu x64/ARM64 bestanden; beide endgültigen
frischen Ubuntu-Paketinstallationen erfolgreich. Der Mac-Tarball wurde erneut
entpackt und mit der echten Aufnahme geprüft. Paket-/Decoderprüfsummen sowie
der vollständige Debian-Lizenztext wurden zusätzlich direkt aus den Archiven
kontrolliert. Auf Ubuntu bestand derselbe Launcherpfad aus dem Installationspräfix
auf dem eigenen CPU-Agenten. Beide Integrationstests erkennen den bekannten
18-Wörter-Clip fehlerfrei; ihre Laufzeiten von 18,69 s (Mac) und 18,56 s (Ubuntu)
umfassen zeitgetreue Zuspielung und sind keine Mikrofon-/Einfügelatenz.

Die vollständige numerische [Evidenz](../benchmarks/reports/profiles-2026-09-07/index.json)
ordnet jede Messung ihrem Code, Artefakt und Workflow zu. Der wiederholte
Beam-5-Sprachpilot bestätigt 8,84 % saubere und 24,62 % 10-dB-WER. Der Gesamtworkflow
ist wegen des bisherigen Geist-Standards und des Beam-1-Vergleichs weiterhin rot;
diese Befunde werden nicht durch erfolgreiche Installation aufgehoben.

## Nächster Schritt im Produktplan

Die grundlegende Profilintegration ist implementiert. Offen bleiben portable
Distributionsbuilds mit Abnahme der exakt ausgelieferten Artefakte, der additive
Sitzungs-/Ereignisvertrag, 30/60-Minuten-Abnahmen, echte Mikrofone und die fünf
verbindlichen Anwendungen. Geführter Erststart, Mikrofonwahl, Shortcut-Einrichtung
und externe Nutzertests folgen. Ein „One-Click“-Versprechen ist noch nicht belegt.
