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
case "$VERSION" in ''|*[!0-9A-Za-z.+:~_-]*) echo 'invalid package version' >&2; exit 1;; esac
PROFILE="${GEIST_PACKAGE_PROFILE:-geist}"
case "$PROFILE" in
geist) BINARY=./diktat; CORE_NAME=diktat;;
whisper-small) BINARY=build/whisper-resident/diktat-whisper; CORE_NAME=diktat-whisper;;
*) echo 'invalid package profile' >&2; exit 1;;
esac
ARCH="$(uname -m)"
case "$(uname -s)" in
Darwin) OS=macos ;;
*)      OS=linux ;;
esac
NAME="geist-diktat_${VERSION}_${OS}-${ARCH}"
STAGE="build/$NAME"

test -x "$BINARY" || { echo "build selected decoder first: $BINARY" >&2; exit 1; }

rm -rf "$STAGE"
mkdir -p "$STAGE/bin" "$STAGE/share/geist-diktat"
python3 packaging/stage-runtime.py "$STAGE" --profile "$PROFILE"
strip "$STAGE/bin/$CORE_NAME" 2>/dev/null || true
python3 packaging/stage-runtime.py "$STAGE" --finalize
install -m644 README.md LICENSE "$STAGE/"

# A shipped binary must not reach past what the platform guarantees.
# macOS: the system frameworks, present on every Mac. Linux: nothing at all —
# the tarball is the "runs on any distro" artifact, so it is linked static
# against musl and must carry no dynamic section. readelf, not ldd: musl and
# glibc word their ldd output differently, the ELF header does not.
case "$OS" in
macos)
    if otool -L "$STAGE/bin/$CORE_NAME" | tail -n +2 | grep -qvE '/usr/lib/|/System/Library/'; then
        echo "diktat links a non-system library — rebuild with GEIST_STATIC_OMP=1" >&2
        otool -L "$STAGE/bin/$CORE_NAME" | tail -n +2 >&2
        exit 1
    fi
    ;;
linux)
    if ! readelf -d "$STAGE/bin/$CORE_NAME" 2>/dev/null | grep -q "There is no dynamic section"; then
        echo "diktat is not statically linked — build it on musl with EXTRA_LDFLAGS=-static" >&2
        readelf -d "$STAGE/bin/$CORE_NAME" 2>&1 | head -20 >&2
        exit 1
    fi
    ;;
esac

tar -C build -czf "$NAME.tar.gz" "$NAME"
echo "built: $NAME.tar.gz"
