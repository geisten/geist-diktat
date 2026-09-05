# geist-diktat

System-wide **local** dictation for Linux — one static binary on the
[geist](https://github.com/geisten/geistlib) engine. No cloud, no Python
stack, no Whisper pipeline: Gemma 4 E2B hears directly (measured on this
engine: **4.2 % WER English** / **7.1 % German**, LibriSpeech / FLEURS —
methodology in geistlib's `benchmark/results/PI5-audio.md`).

A streaming energy VAD segments your speech while you talk; each
utterance becomes one line of clean, punctuated text on stdout. Typing
into the focused window is composition, not configuration:

```sh
arecord -f S16_LE -r 16000 -c 1 -t raw | ./diktat model.gguf | wtype -   # wlroots
arecord ... | ./diktat model.gguf | while IFS= read -r l; do ydotool type -- "$l "; done  # GNOME
```

## Install (Ubuntu, .deb)

```sh
# amd64; use _arm64.deb on ARM (Pi 5, ARM servers)
curl -fLO https://github.com/geisten/geist-diktat/releases/latest/download/geist-diktat_amd64.deb
sudo apt install ./geist-diktat_amd64.deb
geist-diktat setup                 # per-user model download (~3.7 GB, SHA-pinned)
```

Non-Debian distros: grab the `linux-{x86_64,aarch64}.tar.gz` from the
same release — unpack anywhere, `bin/geist-diktat` works in place.

## macOS (Apple Silicon)

```sh
curl -fsSL https://raw.githubusercontent.com/geisten/geist-diktat/main/install.sh | sh
brew install sox        # mic capture; ffmpeg works too
geist-diktat setup      # model (~3.7 GB, SHA-pinned)
geist-diktat run        # transcript lines on stdout
```

The core is the same engine and the same model. What macOS does **not**
get is the typing path: there is no IBus, so `run` gives you the
transcript stream to pipe wherever you want. `GEIST_DIKTAT_CAPTURE`
overrides the capture command when the default mic is not the right one.

Intel Macs are not built — geistlib's mac target compiles the `cpu_neon`
backend. Build from source with a scalar backend if you need one.

Then dictate: run `ibus restart`, add the input source *geist-diktat
(Diktat)* (GNOME Settings → Keyboard → Input Sources, listed under
German), and switch to it with `Super+Space`. Selecting the source starts
the mic; switching away stops it. Committed text arrives through the
standard input-method protocol — no root, no uinput, and every IBus-aware
app (GTK, Qt, Electron, VTE terminals) receives it.

Prefer to wire the typing yourself? `geist-diktat run` prints transcript
lines on stdout; compose them as in the snippet above.

## Build from source

```sh
git clone https://github.com/geisten/geist-diktat
cd geist-diktat
make                    # clones + builds the pinned geistlib, then diktat
make setup              # model (~3.1 GB) + audio tower (~590 MB), SHA-pinned
arecord -q -f S16_LE -r 16000 -c 1 -t raw | \
  ./diktat geistlib/gguf_artifacts/gemma4-e2b-Q4_K_M.gguf   # transcript lines on stdout
sh packaging/build-deb.sh   # roll your own .deb (Linux)
```

Needs ~4 GB RAM (Gemma 4 E2B Q4_K_M); runs on any x86-64 desktop and on
a Raspberry Pi 5. `GEIST_DIKTAT_PROMPT` overrides the transcription
instruction; the default handles English and German without
configuration.

## Status / roadmap

- [x] dictation core (`diktat`, from geistlib's example) — #1
- [ ] `.deb` package: two-command install — #2
- [ ] IBus engine: dictation as an input source in every app, no root — #3
- [ ] Neovim plugin: `:Diktat`, mode-aware insertion via job-control — #4

Working name `geist-diktat`; product-name candidate: `geistschreiber`.

## License

Apache-2.0, same as the engine.

## Integration und Diagnose

`geist-diktat doctor --verify` prüft die Installation.
`geist-diktat editor-install all` installiert die asynchronen Vim-/Neovim-Adapter.
[Prozessvertrag, Shortcuts, Linux-Einbettung und macOS-App](doc/EMBEDDING.md)
beschreiben den aktuellen Entwicklungsstand und seine Grenzen.
