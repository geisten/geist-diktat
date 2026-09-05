#!/bin/sh
# Run after package_ubuntu.sh in the same disposable container, with the
# SHA-pinned model/tower mounted read-only at /model.gguf and /tower.safetensors.
set -eu
cd "$(dirname "$0")/.."
echo '740185b21d22ceb83a11c3aa62ad5842ef32c70f6096d756bbee85a1e4ec34b8  /model.gguf' | sha256sum -c -
echo 'd6c45a6c276212dc3a793e66dfc588d89c12d1ac92c0e4b85494390ca848cd77  /tower.safetensors' | sha256sum -c -
export OMP_NUM_THREADS=4 AUDIT_TIMEOUT=90
export GEIST_AUDIO_MODEL_PATH=/tower.safetensors
export GEIST_MEL_CONSTANTS_PATH="$PWD/geistlib/audio_test_data/mel_constants.bin"
export GEIST_DIKTAT_CMD="python3 -c 'import sys,wave; w=wave.open(\"tests/fixtures/librispeech-1089-134691-0016.wav\"); sys.stdout.buffer.write(w.readframes(w.getnframes())+bytes(32000))' | /usr/bin/diktat /model.gguf"
export IBUS_TEST_EXPECTED='They were voyaging across the deserts of the sky, a host of nomads on the march, voyaging high over Ireland, westward bound. '
sh tests/toolkit_isolated.sh gtk
sh tests/toolkit_isolated.sh qt
echo 'PASS: fixture WAV -> installed real diktat/model -> IBus -> GTK3 and Qt5'
