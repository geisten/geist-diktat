# Project audit tests

These tests execute the application code at `fa9001f` (unchanged by the build
migration through `ebb4987`) and the subsequently added engine-sync script.
**The audit suite is intentionally red on those revisions.** Failures are
ordinary assertions, not `xfail` or silent skips.
The original `make test` smoke target is preserved.

```sh
# First provision the pinned engine headers via the normal build (`make`).
# macOS: Apple clang with C23 support; Linux/Pi: GCC 14 or Clang 19.
CC=cc python3 -m unittest discover -s tests -p 'test_*.py' -v
# Equivalent convenience entry point:
CC=cc sh tests/audit.sh
# Actual Vim when the distribution's `vim` alternative points to Neovim:
VIM_BINARY=/usr/bin/vim.basic CC=gcc-14 python3 -m unittest discover -s tests -v

# Disposable Ubuntu 24.04, including real GTK3/Qt5 text widgets on Xvfb:
docker build -f tests/ubuntu.Dockerfile -t geist-diktat-audit .
docker run --rm -v "$PWD:/work" geist-diktat-audit
```

`core_stub.c` includes the real `src/diktat.c` and replaces only the geist API.
The suite compiles it with AddressSanitizer and UndefinedBehaviorSanitizer.
It checks VAD onset/offset, the 500 ms minimum, 28 s maximum, interrupted
onset, multiple utterances, EOF, partial frames, RMS parsing, setup/stream
failure injection, cleanup, repetition/meta guards, output limits and Unicode.
This does not validate neural-network kernels or speech accuracy.

`test_editors.py` uses real Vim/Neovim processes. The Lua contract suite uses
real buffers and controlled job callbacks/mode responses for reproducible
split-read and lifecycle races; a separate real subprocess reproduces split
stdout. `:read !…` tests a **finite** Vim import, not an asynchronous Vim plugin.
`benchmarks/editors.py` measures the happy path independently.

`test_launcher.py` and `test_installer.py` use temporary prefixes, HOME and
PATH with fake external commands. They perform no real download, microphone
capture or host installation. They test quoting, relocation, error propagation,
checksum/architecture gates, and preserving an existing installation when
unpacking fails. They do not constitute a signed-release/security audit.

`ibus_lifecycle.c` includes the real adapter and tests its process management
without a desktop. It explicitly reaps its own test children afterwards.
`ibus_isolated.sh` uses a private component registry, private IBus address and
private D-Bus session. `toolkit_isolated.sh` tests actual GTK/Qt IBus modules.
Neither script replaces a running desktop daemon nor writes system registry
files. Exit 77 means a missing optional IBus toolchain, not a passing test.
Container runs need GNU `timeout`, IBus, D-Bus, pkg-config, GTK3/Qt5 development
packages, ibus-gtk3, Xvfb, xauth and xdotool; the Dockerfile provisions them.

`package_ubuntu.sh` builds and installs the actual .deb inside that disposable
image, retaining its artifact under `build/ubuntu-package`. For a clean runtime
dependency check without compiler/development packages:

```sh
docker run --rm -v "$PWD:/work" geist-diktat-audit sh tests/package_ubuntu.sh
docker run --rm -v "$PWD/build/ubuntu-package:/packages:ro" \
  -v "$PWD/tests/runtime_ubuntu.sh:/runtime-test.sh:ro" \
  ubuntu:24.04 sh /runtime-test.sh
```

`toolkit_real.sh` runs the WAV through the installed actual model/binary into
GTK3 and Qt5. Run it in the **same container** after `package_ubuntu.sh`, with
the pinned model/tower mounted read-only as `/model.gguf` and
`/tower.safetensors`. It verifies both hashes. The production microphone stage
is replaced by fixture PCM; the production engine is built separately from
the adapter with the test-only pipeline hook.

`results/` contains the observed host/Ubuntu logs. Test names and subtest
arguments identify each failed contract. Missing editors are explicitly
skipped. A distribution may make `/usr/bin/vim` a Neovim alias; that is not
evidence of Vim compatibility.

For real model tests and performance measurements see
[`../benchmarks/README.md`](../benchmarks/README.md).

## Erweiterung: Sprachqualität und gemessene Abdeckung

`sh tests/coverage.sh` exportiert LLVM-Zeilen-/Zweigabdeckung des tatsächlichen C-Cores, auch wenn Regressionen rot bleiben. `test_quality.py` prüft die WER-Metrik, `test_core.py` zusätzlich 30:20 Minuten/1.400 Äußerungen im Fake-Engine-Stresstest und die x86-Backendauswahl. Das ist keine Abdeckung des neuronalen Engine-Codes. Echte deutsche, Dialekt-, Rausch- und Gesprächsdaten werden getrennt durch `benchmarks/quality.py` ausgewertet. Details: [Qualitätsbericht](../doc/QUALITY-2026-09-05.md).
