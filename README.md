# geist-diktat

Lokales Diktieren mit dem C-Core der [geist-Engine](https://github.com/geisten/geistlib)
und Gemma 4 E2B. Der Core verarbeitet PCM-Audio und liefert UTF-8-Transkriptzeilen.
Der Launcher verwendet Python 3 aus der Standardbibliothek zur Aufnahmeüberwachung,
Fehlerweitergabe und Begrenzung des Audiopuffers. Audiodaten werden nicht hochgeladen.

**Entwicklungsstand:** Diese Änderungen sind noch keine Produktfreigabe. Ältere
GitHub-Releases enthalten die neuen Adapter und Diagnosebefehle noch nicht.
Die gemessene deutsche Pilot-WER beträgt beim Geist-Pfad 16,0 % auf macOS im
ursprünglichen Audit und erneut 20,7 % auf dem Pi5. Rauschen und lange Gespräche
bleiben Freigabeblocker. [Messmethodik und Grenzen](doc/QUALITY-2026-09-05.md),
[Umsetzungsplan](doc/PRODUCT-PLAN.md),
[Implementierung und neue Test-/Vergleichsergebnisse](doc/IMPLEMENTATION-2026-09-06.md).

## Ubuntu / Linux

Nach Installation eines passenden .deb aus diesem Quellstand:

```sh
geist-diktat setup                 # Modelle herunterladen und SHA-256 prüfen
geist-diktat doctor --verify       # Dateien, Programme und Prüfsummen prüfen
geist-diktat editor-install all    # optional: Vim und Neovim
geist-diktat run                   # Mikrofon -> Transkriptzeilen
```

Das .deb benötigt IBus für systemweite Texteingabe. Bei Bedarf ab- und wieder
anmelden und die Eingabequelle **geist-diktat (Diktat)** hinzufügen. Aufnahme
startet im aktivierten, fokussierten Eingabekontext; Fokusverlust und Abschalten
stoppen sie. Passwort-, PIN- und als privat gekennzeichnete Felder starten keine
Aufnahme. GTK3 und Qt5 sind unter isoliertem Xorg/Xvfb getestet; daraus folgt
keine Freigabe sämtlicher Wayland-, Browser- oder sandboxierter Anwendungen.

Für einen ausdrücklich gewählten, mit `wtype` kompatiblen Wayland-Compositor:

```sh
# In Bash sorgt pipefail für die Weitergabe beider Pipeline-Fehler.
set -o pipefail
geist-diktat run | geist-diktat type wtype --
```

Der Adapter übergibt jede fertige Zeile als ein Argument und wartet nicht auf
EOF der gesamten Aufnahmesitzung. Für Fokus- und Schutzfeldregeln siehe
[Einbettungsvertrag](doc/EMBEDDING.md).

## Vim und Neovim

Nach `geist-diktat editor-install all` den Editor neu starten. `:DiktatToggle`
startet/stoppt; `:DiktatStart` und `:DiktatStop` sind ebenfalls verfügbar.
Eine persönliche Taste lässt sich über `<Plug>(DiktatToggle)` zuweisen:

```vim
nmap <F8> <Plug>(DiktatToggle)
imap <F8> <Plug>(DiktatToggle)
```

Die Installation verändert keine vimrc/init.lua. Die Adapter verarbeiten
fragmentierte UTF-8-Ausgabe asynchron und behandeln Diktat als Text, auch im
Normalmodus. Alte Sitzungs-Callbacks können nicht in eine neue Sitzung schreiben.

## macOS / Apple Silicon

Der CLI-Launcher benötigt Python 3 und `sox` oder `ffmpeg` zur Aufnahme.
`GEIST_DIKTAT_CAPTURE` erlaubt eine eigene vertrauenswürdige Recorder-Konfiguration.
Die native Menüleisten-App lässt sich aus einem gebauten Core erzeugen:

```sh
make GEIST_STATIC_OMP=1
sh macos/build-app.sh
open 'build/Geist Diktat.app'
```

Sie bietet Einrichtung, Diagnose, Start/Stop mit Ctrl-Option-Leertaste,
Transkriptvorschau, Kopieren und optionales Einfügen über Bedienungshilfen.
Die App ist ein Entwicklungsprototyp, standardmäßig nur ad hoc signiert und
nicht notarisiert. Mikrofon- und Bedienungshilfenrechte sind interaktiv nötig;
eine vollständige TextEdit-/Browser-/Terminal-Abnahme steht aus. Intel-Macs
werden in diesem Projekt weiterhin nicht als Release-Ziel gebaut.

## Aus Quellen bauen und testen

```sh
git clone https://github.com/geisten/geist-diktat
cd geist-diktat
make                       # gepinnte Engine synchronisieren und Core bauen
make setup                 # Modelle für den direkten Core-Test herunterladen
python3 -m unittest discover -s tests -p 'test_*.py' -v
sh tests/coverage.sh        # LLVM-Coverage des Core mit kontrollierter Engine
```

Unter Linux werden GCC 14, libibus-1.0-dev und die in
[tests/ubuntu.Dockerfile](tests/ubuntu.Dockerfile) aufgeführten Testabhängigkeiten
verwendet. `make ibus` baut die Integration; `sh packaging/build-deb.sh` erzeugt
das .deb. macOS-Tarballs: `sh packaging/build-tarball.sh` nach einem Build mit
statisch eingebundenem OpenMP. Linux-Tarballs benötigen einen statischen musl-Build.

Die Messungen auf dem 4-GiB-Pi5 zeigen rund 2,9 GiB Spitzen-RSS für den Core;
auf dem Mac liegt der FP32-Audiopfad bei rund 6,3 GiB. Eine kleine Modell-Datei
ist keine Zusage entsprechend niedrigen Laufzeitspeichers. Der begrenzte
Launcher stoppt bei Überlast sichtbar mit Exit 75; kontinuierliches Diktieren
ist auf dem Pi5 noch nicht freigegeben.

[Tests](tests/README.md), [Benchmarks](benchmarks/README.md),
[Einbettung und tägliche Bedienung](doc/EMBEDDING.md).

## Lizenz

Apache-2.0. Der experimentelle whisper.cpp-Vergleich in `benchmarks/` ist ein
separat zu bauender Vergleichsbackend und gehört nicht zum standardmäßig
ausgelieferten Erkennungspfad.
