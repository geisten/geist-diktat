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
sudo usermod -aG input $USER       # once, for ydotool typing; then re-login
```

Non-Debian distros: grab the `linux-{x86_64,aarch64}.tar.gz` from the
same release — unpack anywhere, `bin/geist-diktat` works in place.

Two ways to dictate, pick one:

**IBus input source (recommended — no root, works in every IBus-aware
app):** run `ibus restart`, add the input source *geist-diktat (Diktat)*
(GNOME Settings → Keyboard → Input Sources, listed under German), then
switch to it with `Super+Space`. Selecting the source starts the mic;
switching away stops it. Committed text arrives through the standard
input-method protocol.

**Hotkey + ydotool (fallback):** bind `geist-diktat toggle` to a custom
shortcut — press it, speak, press it again. Needs the `input` group
membership from above.

## Build from source

```sh
git clone --recurse-submodules https://github.com/geisten/geist-diktat
cd geist-diktat
make                    # builds diktat against the pinned geistlib
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
- [ ] `.deb` package: two-command install, hotkey toggle, ydotool wiring — #2
- [ ] IBus engine: dictation as an input source in every app, no root — #3
- [ ] Neovim plugin: `:Diktat`, mode-aware insertion via job-control — #4

Working name `geist-diktat`; product-name candidate: `geistschreiber`.

## License

Apache-2.0, same as the engine.
