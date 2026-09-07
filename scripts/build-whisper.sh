#!/bin/sh
# Experimental resident candidate. Keeps the default Geist build untouched.
set -eu
cd "$(dirname "$0")/.."
GEIST_REPO=https://github.com/ggml-org/whisper.cpp.git \
GEIST_REF=52a939a2a762224e255d366c1182b2af4dd1a032 \
GEISTLIB=build/whisper.cpp sh scripts/sync-engine.sh
case "${GEIST_WHISPER_BLAS:-0}" in
0) BLAS=OFF ;;
1) BLAS=ON ;;
*) echo 'GEIST_WHISPER_BLAS must be 0 or 1' >&2; exit 1 ;;
esac
cmake -S whisper -B build/whisper-resident -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 -DWHISPER_SOURCE="$PWD/build/whisper.cpp" \
    -DGEIST_WHISPER_BLAS="$BLAS" -DGGML_BLAS_VENDOR="${GEIST_WHISPER_BLAS_VENDOR:-Generic}"
cmake --build build/whisper-resident --target diktat-whisper -j "${GEIST_BUILD_JOBS:-4}"
