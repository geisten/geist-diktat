#!/bin/sh
# geist-diktat installer — one-liner entry point.
#
#   curl -fsSL https://raw.githubusercontent.com/geisten/geist-diktat/main/install.sh | sh
#
# Debian/Ubuntu: downloads the latest release .deb for this architecture
# and installs it via apt (the only sudo step, announced first).
# Other distros and macOS: unpacks the tarball to ~/.local/geist-diktat.
set -eu

REPO="geisten/geist-diktat"
BASE="https://github.com/$REPO/releases/latest/download"

case "$(uname -m)" in
x86_64) DEB_ARCH=amd64 ;;
aarch64 | arm64) DEB_ARCH=arm64 ;;
*)
    echo "geist-diktat: unsupported architecture: $(uname -m)" >&2
    echo "(supported: x86_64, aarch64 — build from source: https://github.com/$REPO)" >&2
    exit 1
    ;;
esac

case "$(uname -s)" in
Linux)  OS=linux ;;
Darwin) OS=macos ;;
*)
    echo "geist-diktat: Linux and macOS only (got $(uname -s)) — build from source" >&2
    exit 1
    ;;
esac

if [ "$OS" = macos ] && [ "$(uname -m)" != arm64 ]; then
    echo "geist-diktat: macOS builds are Apple Silicon only (got $(uname -m))" >&2
    echo "(the engine's mac target builds the cpu_neon backend)" >&2
    exit 1
fi

TMP=$(mktemp -d)
STAGE='' BACKUP='' DEST='' LOCK=''
cleanup() {
    if [ -n "$BACKUP" ] && [ -e "$BACKUP" ] && [ ! -e "$DEST" ]; then mv "$BACKUP" "$DEST"; fi
    [ -z "$STAGE" ] || rm -rf "$STAGE"
    [ -z "$LOCK" ] || rmdir "$LOCK"
    rm -rf "$TMP"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# Every asset is checked against the release's own SHA256SUMS before it is
# installed — this catches a truncated download or a swapped asset, not a
# compromised release. v0.1.2 predates that manifest, so keep its independently
# verified hashes as a narrow migration path. Any other manifest-less release
# still fails closed because its assets cannot match these pins.
# ponytail: signature verification (gh attestation / minisign) is the upgrade
# path once releases are signed.
if ! curl -fL --retry 3 -o "$TMP/SHA256SUMS" "$BASE/SHA256SUMS"; then
    echo "geist-diktat: release manifest unavailable; trying pinned v0.1.2 hashes" >&2
    cat > "$TMP/SHA256SUMS" <<'EOF'
3b6dfb85983f47346858f4a5a7cfd0f31366b30ce74b5e6118595f9b0cbf55f0  geist-diktat_amd64.deb
28083701f8ee1afce25e04ecd0aa2e4f2f33b85af9bde0bf19a4dc8a2ad26486  geist-diktat_arm64.deb
9d9054bf7695dbbed9d795da11f07fdd4427b704bc4f12b169db78746f01f678  geist-diktat_linux-x86_64.tar.gz
250f05ad8a510aaf16733e52dfed307557e6e88a2294ee201151576099a8c058  geist-diktat_linux-aarch64.tar.gz
EOF
fi

sha256_of() { (sha256sum "$1" 2>/dev/null || shasum -a 256 "$1") | cut -d' ' -f1; }

verify() { # $1 = downloaded file, $2 = asset name as listed in SHA256SUMS
    want=$(sed -n "s|^\([0-9a-f]\{64\}\) [ *]$2\$|\1|p" "$TMP/SHA256SUMS" | head -1)
    [ -n "$want" ] || { echo "geist-diktat: $2 not listed in SHA256SUMS" >&2; exit 1; }
    [ "$(sha256_of "$1")" = "$want" ] || { echo "geist-diktat: checksum mismatch for $2" >&2; exit 1; }
    echo "checksum ok: $2"
}

if [ "$OS" = linux ] && command -v apt-get >/dev/null 2>&1; then
    DEB="geist-diktat_$DEB_ARCH.deb"
    echo "downloading $DEB ..."
    curl -fL --retry 3 -o "$TMP/$DEB" "$BASE/$DEB"
    verify "$TMP/$DEB" "$DEB"
    if [ "$(id -u)" = 0 ]; then
        apt-get install -y "$TMP/$DEB"
    else
        echo "installing via apt (needs sudo):"
        echo "  sudo apt-get install -y $TMP/$DEB"
        sudo apt-get install -y "$TMP/$DEB"
    fi
else
    TAR="geist-diktat_${OS}-$(uname -m).tar.gz"
    DEST="$HOME/.local/geist-diktat"
    echo "no apt found — unpacking the $OS tarball to $DEST ..."
    curl -fL --retry 3 -o "$TMP/$TAR" "$BASE/$TAR"
    verify "$TMP/$TAR" "$TAR"
    mkdir -p "$HOME/.local"
    if mkdir "$HOME/.local/.geist-diktat-install.lock" 2>/dev/null; then
        LOCK="$HOME/.local/.geist-diktat-install.lock"
    else
        echo "geist-diktat: another installation is active (or stale install lock); previous version preserved" >&2
        exit 1
    fi
    STAGE=$(mktemp -d "$HOME/.local/.geist-diktat.XXXXXX")
    tar -C "$STAGE" --strip-components=1 -xzf "$TMP/$TAR"
    [ -x "$STAGE/bin/diktat" ] && [ -x "$STAGE/bin/geist-diktat" ] || {
        echo "geist-diktat: incomplete release; previous installation preserved" >&2; exit 1;
    }
    if [ -e "$DEST" ] || [ -L "$DEST" ]; then
        BACKUP="$STAGE.previous"
        mv "$DEST" "$BACKUP"
    fi
    mv "$STAGE" "$DEST"
    STAGE=''
    [ -z "$BACKUP" ] || echo "previous installation retained: $BACKUP"
    echo "add to PATH: export PATH=\"$DEST/bin:\$PATH\""
fi

echo
echo "Next steps:"
echo "  geist-diktat setup    # model download (~3.7 GB, SHA-pinned)"
if [ "$OS" = macos ]; then
    echo "  brew install sox      # mic capture (ffmpeg also works)"
    echo "  geist-diktat run      # transcript lines on stdout"
    echo
    echo "No IBus on macOS: 'run' gives you the transcript stream to pipe;"
    echo "there is no typing-into-the-focused-app path here."
else
    echo "  geist-diktat doctor   # then add the IBus input source in Settings"
    echo "                        # under Settings -> Keyboard (listed under German)"
fi
