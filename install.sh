#!/bin/sh
# geist-diktat installer — one-liner entry point.
#
#   curl -fsSL https://raw.githubusercontent.com/geisten/geist-diktat/main/install.sh | sh
#
# Debian/Ubuntu: downloads the latest release .deb for this architecture
# and installs it via apt (the only sudo step, announced first).
# Other distros: unpacks the static tarball to ~/.local/geist-diktat.
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

[ "$(uname -s)" = Linux ] || {
    echo "geist-diktat: Linux only (got $(uname -s)) — build from source on other systems" >&2
    exit 1
}

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

# Every asset is checked against the release's own SHA256SUMS before it is
# installed — this catches a truncated download or a swapped asset, not a
# compromised release. ponytail: signature verification (gh attestation /
# minisign) is the upgrade path once releases are signed.
curl -fL --retry 3 -o "$TMP/SHA256SUMS" "$BASE/SHA256SUMS"

sha256_of() { (sha256sum "$1" 2>/dev/null || shasum -a 256 "$1") | cut -d' ' -f1; }

verify() { # $1 = downloaded file, $2 = asset name as listed in SHA256SUMS
    want=$(sed -n "s|^\([0-9a-f]\{64\}\) [ *]$2\$|\1|p" "$TMP/SHA256SUMS" | head -1)
    [ -n "$want" ] || { echo "geist-diktat: $2 not listed in SHA256SUMS" >&2; exit 1; }
    [ "$(sha256_of "$1")" = "$want" ] || { echo "geist-diktat: checksum mismatch for $2" >&2; exit 1; }
    echo "checksum ok: $2"
}

if command -v apt-get >/dev/null 2>&1; then
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
    TAR="geist-diktat_linux-$(uname -m).tar.gz"
    DEST="$HOME/.local/geist-diktat"
    echo "no apt found — unpacking the static tarball to $DEST ..."
    curl -fL --retry 3 -o "$TMP/$TAR" "$BASE/$TAR"
    verify "$TMP/$TAR" "$TAR"
    rm -rf "$DEST"
    mkdir -p "$DEST"
    tar -C "$DEST" --strip-components=1 -xzf "$TMP/$TAR"
    echo "add to PATH: export PATH=\"$DEST/bin:\$PATH\""
fi

cat <<'EOF'

Next steps:
  geist-diktat setup                 # model download (~3.7 GB, SHA-pinned)
  sudo usermod -aG input $USER       # once, for ydotool typing; re-login after
Then either add the IBus input source "geist-diktat (Diktat)" (recommended,
run `ibus restart` first) or bind `geist-diktat toggle` to a hotkey.
EOF
