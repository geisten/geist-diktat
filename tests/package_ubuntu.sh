#!/bin/sh
# Build/install in a disposable Ubuntu container. Never run on the host.
set -eu
cd "$(dirname "$0")/.."
test -f /.dockerenv || { echo 'Run this only in tests/ubuntu.Dockerfile'; exit 2; }
STAGE=$(mktemp -d)
OUTPUT="$PWD/build/ubuntu-package"
mkdir -p "$OUTPUT"
trap 'rm -rf "$STAGE"' EXIT
# Use an independent build tree so the native Pi benchmark binary is retained.
cp -a geistlib src ibus packaging README.md LICENSE "$STAGE/"
mkdir -p "$STAGE/scripts"
test ! -d scripts || cp -a scripts/. "$STAGE/scripts/"
cp Makefile "$STAGE/Makefile"
# The engine is copied as source; the container has no git metadata. Link via
# the engine's own build flags, then invoke the actual package builder.
(
    cd "$STAGE"
    make -C geistlib -j4 CC=gcc-14 TARGET=linux GEMM_PROVIDER=native lib
    gcc-14 -std=c23 -O2 -Igeistlib/include -fopenmp src/diktat.c \
        geistlib/lib/linux/release/libgeist.a -lm -o diktat
    gcc-14 -std=c23 -O2 $(pkg-config --cflags ibus-1.0) ibus/engine.c \
        $(pkg-config --libs ibus-1.0) -o ibus-engine-geist-diktat
    VERSION=0.1.0 sh packaging/build-deb.sh
    cp diktat geist-diktat_*.deb "$OUTPUT/"
    dpkg-deb --info geist-diktat_*.deb
    apt-get update -q
    apt-get install -y -q ./geist-diktat_*.deb
)
set +e
geist-diktat > "$STAGE/usage" 2>&1
status=$?
set -e
test "$status" = 2
grep -q usage "$STAGE/usage"
set +e
diktat /nonexistent/model.gguf </dev/null > "$STAGE/missing" 2>&1
status=$?
set -e
test "$status" = 1
grep -q 'model_load failed' "$STAGE/missing"
command -v arecord
command -v curl
test -f /usr/share/ibus/component/geist-diktat.xml
test -x /usr/libexec/ibus-engine-geist-diktat
echo 'PASS: source build, deb metadata, apt install and installed launcher/engine sanity'
