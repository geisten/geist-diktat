#!/bin/sh
# build-tarball.sh — tarball for non-Debian distros and for macOS.
#
#   make TARGET=linux GEMM_PROVIDER=native EXTRA_LDFLAGS=-static   # linux, on musl
#   make GEIST_STATIC_OMP=1                            # macOS (arm64 only)
#
# macOS needs GEIST_STATIC_OMP=1: without it the binary hard-links
# /opt/homebrew/opt/libomp/lib/libomp.dylib and the tarball is broken on
# any Mac that has no Homebrew libomp at that path. Checked below.
# Apple Silicon only — geistlib's mac targets build cpu_neon, so there
# is no Intel Mac build.
#   sh packaging/build-tarball.sh    # -> geist-diktat_<v>_<os>-<arch>.tar.gz
#
# The layout mirrors the installed /usr prefix (bin/, share/geist-diktat/),
# and the wrapper derives its prefix from its own location — the same
# file works installed and unpacked, no patching:
#   tar xf geist-diktat_*.tar.gz && geist-diktat_*/bin/geist-diktat setup
set -e
cd "$(dirname "$0")/.."

VERSION="${VERSION:-0.1.0}"
ARCH="$(uname -m)"
case "$(uname -s)" in
Darwin) OS=macos ;;
*)      OS=linux ;;
esac
NAME="geist-diktat_${VERSION}_${OS}-${ARCH}"
STAGE="build/$NAME"

test -x ./diktat || { echo "build ./diktat first (make)" >&2; exit 1; }

rm -rf "$STAGE"
mkdir -p "$STAGE/bin" "$STAGE/share/geist-diktat"
install -m755 diktat "$STAGE/bin/diktat"
strip "$STAGE/bin/diktat" 2>/dev/null || true   # advisory: BSD strip is pickier
install -m755 packaging/geist-diktat "$STAGE/bin/geist-diktat"
install -m644 geistlib/audio_test_data/mel_constants.bin "$STAGE/share/geist-diktat/"
install -m755 geistlib/tools/fetch_audio_tower.py "$STAGE/share/geist-diktat/"
install -m644 README.md LICENSE "$STAGE/"

# A shipped binary must not reach past what the platform guarantees.
# macOS: the system frameworks, present on every Mac. Linux: nothing at all —
# the tarball is the "runs on any distro" artifact, so it is linked static
# against musl and must carry no dynamic section. readelf, not ldd: musl and
# glibc word their ldd output differently, the ELF header does not.
case "$OS" in
macos)
    if otool -L "$STAGE/bin/diktat" | tail -n +2 | grep -qvE '/usr/lib/|/System/Library/'; then
        echo "diktat links a non-system library — rebuild with GEIST_STATIC_OMP=1" >&2
        otool -L "$STAGE/bin/diktat" | tail -n +2 >&2
        exit 1
    fi
    ;;
linux)
    if ! readelf -d "$STAGE/bin/diktat" 2>/dev/null | grep -q "There is no dynamic section"; then
        echo "diktat is not statically linked — build it on musl with EXTRA_LDFLAGS=-static" >&2
        readelf -d "$STAGE/bin/diktat" 2>&1 | head -20 >&2
        exit 1
    fi
    ;;
esac

tar -C build -czf "$NAME.tar.gz" "$NAME"
echo "built: $NAME.tar.gz"
