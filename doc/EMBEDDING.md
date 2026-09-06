# Einbettung und tägliche Bedienung

## Prozessvertrag v1

`geist-diktat run [RMS]` nimmt lokal auf und schreibt **eine abgeschlossene Äußerung
pro UTF-8-Zeile** nach stdout. Keine Statusmeldungen auf stdout. Pipe-Reads sind
keine Nachrichtengrenzen: Empfänger müssen bis `\n` puffern, auch mitten in einem
UTF-8-Zeichen. Ein letzter Rest bei regulärem EOF ist eine vollständige letzte
Nachricht. Ein expliziter Stop verwirft noch nicht zugestellte Ausgabe der Sitzung.
Maximal 64 KiB je Nachricht akzeptieren. Text als Daten behandeln; niemals als
Shell-/Editorbefehl ausführen. Leere Zeilen ignorieren.

Der C-Core `diktat MODEL [RMS]` liest PCM16LE, mono, 16000 Hz von stdin. Ein
abschließendes halbes Sample ist ein Eingabefehler; ein kürzerer vollständiger
Frame wird verarbeitet. EOF finalisiert die laufende Äußerung. RMS muss eine
endliche Zahl im Bereich `(0, 32768]` sein, Standard 300.

Der Launcher benötigt Python 3. Er trennt Aufnahme und Decoder durch eine
begrenzte Queue. `GEIST_DIKTAT_BUFFER_SECONDS` stellt 0,1–60 Sekunden ein,
Standard 6. Das begrenzt den Audio-Rückstand im eigenen Benutzerpuffer;
Betriebssystem-Pipes und Recorder besitzen zusätzliche kleine Puffer. Überschreitung
stoppt den gesamten Prozessbaum sichtbar mit Exit **75**. Es werden keine Audiodateien
angelegt. Es gibt noch keinen zuverlässigen Wiederanlauf nach Überlast.

Exit 0 bedeutet reguläres Ende. Recorder- und Decoderfehler werden als Fehler
weitergereicht; 70 bezeichnet ein vorzeitiges erfolgreiches Decoder-Ende,
74 einen Lesefehler, 75 Überlast, 130/143 Abbruch per INT/TERM. Status steht auf
stderr. Integrationen dürfen nicht allein das Wort „listening“ als Gerätefreigabe
interpretieren. Start eines Capture-Prozesses beweist keine Mikrofonberechtigung.

Für eigene Capture-Kommandos ist `GEIST_DIKTAT_CAPTURE` eine vom Benutzer
vertrauenswürdig konfigurierte Shell-Zeichenfolge. Diktierter Text darf dort
nicht interpoliert werden. Das Kommando muss PCM16LE liefern, keine WAV-Header.
`GEIST_DIKTAT_CORE`, `GEIST_DIKTAT_MODEL`, `GEIST_AUDIO_MODEL_PATH` und
`GEIST_MEL_CONSTANTS_PATH` unterstützen explizite lokale Pfade.

## Vim und Neovim

Nach Paketinstallation:

```sh
geist-diktat setup
geist-diktat doctor --verify
geist-diktat editor-install all
```

Die Installation legt ein natives `pack/geist/start/geist-diktat`-Paket an,
verändert keine vimrc/init.lua und erhält eine vorhandene Installation als
`geist-diktat.previous-*`. Diese Sicherung außerhalb des `start`-Ordners ablegen,
bevor der Editor neu startet; der Installer legt sie automatisch dort ab.

Editor neu starten; `:DiktatToggle`, `:DiktatStart` und `:DiktatStop` verwenden.
Persönliche Taste in Vim oder Neovim:

```vim
nmap <F8> <Plug>(DiktatToggle)
imap <F8> <Plug>(DiktatToggle)
```

Vim benötigt `+job +channel +timers`, Neovim die Lua-API mit `ModeChanged`.
Vim-Konfiguration: `g:geist_diktat_command` als Argumentliste, optional
`g:geist_diktat_suffix`. Neovim: `require('geist-diktat').setup({launcher=...})`.
Beim Wechsel in einen anderen Buffer wird ausstehender Text nicht dort eingefügt.
Während der Kommandozeile bleibt Text bis zum Verlassen gepuffert. Normalmodus-
Ausgabe wird direkt als Text eingefügt; `:q!` aus einem Diktat führt keinen Befehl aus.
Stop invalidiert auch bereits eingeplante alte Callbacks. Fehler erscheinen sichtbar.

## Linux-Anwendungen

IBus ist der bevorzugte systemweite Pfad. Das .deb registriert die Engine-Datei;
nach Installation bei Bedarf ab- und wieder anmelden, dann die Eingabequelle
„geist-diktat (Diktat)“ in den Systemeinstellungen auswählen. Keine fremde laufende
IBus-Sitzung aus einem Installationsskript neu starten. Fokusverlust/Disable stoppt
die Aufnahme, Passwort/PIN/Private-Felder aktivieren sie nicht.

Für ausdrücklich gewollte direkte Wayland-Einspeisung:

```sh
geist-diktat run | geist-diktat type wtype --
```

Der Adapter startet `wtype` pro fertiger Zeile und übergibt den Text als genau ein
Argument. Er wartet nicht auf das Ende einer unendlichen Aufnahmepipe. Voraussetzung:
Compositor unterstützt das von wtype verwendete Eingabeprotokoll. Die Shell zeigt
standardmäßig den Status des letzten Pipeline-Prozesses; zur Erfassung beider
Fehler in Bash `set -o pipefail` verwenden. Dieser allgemeine Adapter kennt weder
Secure Input noch Fokuswechsel. Für vertrauliche Felder und automatische Auswahl
von Zielanwendungen ausschließlich einen passenden, geprüften Integrationspfad nutzen.

Referenzimplementierungen: `runtime/line_sink.py`, `lua/geist-diktat/init.lua`,
`autoload/geist_diktat.vim`, `ibus/engine.c`.

## macOS-App — Entwicklungsstand

`sh macos/build-app.sh` baut `build/Geist Diktat.app` inklusive Core und Launcher.
Menü: Einrichtung, Diagnose, Start/Stop, Vorschau, Kopieren. Globaler Shortcut:
Ctrl-Option-Leertaste. Direkte Einfügung ist optional und benötigt Bedienungshilfen.
Es werden nur beschreibbare Textfelder mit identischem AX-Ziel angesprochen;
Secure Input und geschützte Felder werden ausgeschlossen. Nicht unterstützte
AX-Anwendungen verwenden die Vorschau. Aufnahme benötigt sox oder ffmpeg und
Python 3. Es gibt noch keine zertifizierte TextEdit-/Browser-/Terminal-Matrix.

Ohne `GEIST_SIGN_IDENTITY` wird ausschließlich ad hoc signiert. Dies ist kein
notarisiertes Vertriebspaket und noch kein nachgewiesener One-Click-Erststart.
Mikrofon- und Bedienungshilfenrechte müssen interaktiv erteilt werden.

## Interne Diagnose für kontrollierte Messungen

`GEIST_DIKTAT_TRACE` aktiviert optional numerische Zeit-/Pufferereignisse in einer
separaten Datei. Der v1-Textvertrag auf stdout bleibt unverändert. Details und
Grenzen stehen in [MEASUREMENT-GATES.md](MEASUREMENT-GATES.md). Diese Diagnose ist
kein öffentlicher Ergebnis-/Statusmodus und keine Mikrofonberechtigungsprüfung.

## Experimenteller residenter CPU-Kandidat

[RESIDENT-ASR.md](RESIDENT-ASR.md) beschreibt den zusätzlichen Whisper-Prozess,
seinen Build und die Verwendung hinter demselben Aufnahme-Supervisor. Sein
PCM16-/UTF-8-Vertrag passt zum bestehenden lokalen Prozesspfad. Die automatische
Backend-Auswahl und Paketintegration sind noch offen; daraus folgt noch keine
Freigabe der fünf Beta-Anwendungen.
