#!/bin/sh
# build-deb.sh — stage and build the geist-diktat .deb with dpkg-deb.
# No debhelper: the layout is small enough to own directly (and the
# engine build already happened via the repo Makefile).
#
#   make CC=gcc-14 TARGET=linux GEMM_PROVIDER=native
#   sh packaging/build-deb.sh            # -> geist-diktat_<v>_<arch>.deb
set -e
cd "$(dirname "$0")/.."

VERSION="${VERSION:-0.1.0}"
ARCH="$(dpkg --print-architecture)"
STAGE="build/geist-diktat_${VERSION}_${ARCH}"

test -x ./diktat || { echo "build ./diktat first (make)" >&2; exit 1; }

rm -rf "$STAGE"
mkdir -p \
    "$STAGE/DEBIAN" \
    "$STAGE/usr/bin" \
    "$STAGE/usr/lib/systemd/user" \
    "$STAGE/usr/lib/udev/rules.d" \
    "$STAGE/usr/share/applications" \
    "$STAGE/usr/share/geist-diktat" \
    "$STAGE/usr/share/doc/geist-diktat"

install -m755 diktat "$STAGE/usr/bin/diktat"
strip "$STAGE/usr/bin/diktat"
# IBus engine (built via `make ibus`; required for the .deb).
test -x ./ibus-engine-geist-diktat || { echo "build the ibus engine first (make ibus)" >&2; exit 1; }
mkdir -p "$STAGE/usr/libexec" "$STAGE/usr/share/ibus/component"
install -m755 ibus-engine-geist-diktat "$STAGE/usr/libexec/"
strip "$STAGE/usr/libexec/ibus-engine-geist-diktat"
install -m644 ibus/geist-diktat.xml "$STAGE/usr/share/ibus/component/"
install -m755 packaging/geist-diktat "$STAGE/usr/bin/geist-diktat"
install -m644 packaging/geist-diktat.service "$STAGE/usr/lib/systemd/user/"
install -m644 packaging/70-geist-diktat-uinput.rules "$STAGE/usr/lib/udev/rules.d/"
install -m644 packaging/geist-diktat.desktop "$STAGE/usr/share/applications/"
# Runtime data the wrapper needs: mel constants (checked into the engine)
# and the SHA-verifying tower fetcher.
install -m644 geistlib/audio_test_data/mel_constants.bin "$STAGE/usr/share/geist-diktat/"
install -m755 geistlib/tools/fetch_audio_tower.py "$STAGE/usr/share/geist-diktat/"
install -m644 README.md "$STAGE/usr/share/doc/geist-diktat/"

# Debian changelog (lintian: required). One generated entry — release
# history lives in git.
gzip -9n > "$STAGE/usr/share/doc/geist-diktat/changelog.gz" <<EOF
geist-diktat ($VERSION) unstable; urgency=low

  * See https://github.com/geisten/geist-diktat/releases

 -- germar <g.schlegel@geisten.net>  $(date -R)
EOF

# Debian copyright file (lintian: required).
cat > "$STAGE/usr/share/doc/geist-diktat/copyright" <<EOF
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: geist-diktat
Source: https://github.com/geisten/geist-diktat

Files: *
Copyright: 2026 geisten.net
License: Apache-2.0
 On Debian systems the full text of the Apache License 2.0 can be found
 in /usr/share/common-licenses/Apache-2.0.
EOF

# OpenMP runtime follows the compiler that built the binary.
if ldd diktat | grep -q libomp; then
    OMP_DEP="libomp5-19 | libomp5"
else
    OMP_DEP="libgomp1"
fi

INSTALLED_SIZE=$(du -sk "$STAGE" | cut -f1)
cat > "$STAGE/DEBIAN/control" <<EOF
Package: geist-diktat
Version: $VERSION
Architecture: $ARCH
Maintainer: germar <g.schlegel@geisten.net>
Installed-Size: $INSTALLED_SIZE
Depends: libc6, $OMP_DEP, alsa-utils, ydotool, curl, python3, libibus-1.0-5
Recommends: libnotify-bin, ibus
Section: sound
Priority: optional
Homepage: https://github.com/geisten/geist-diktat
Description: system-wide local dictation (Gemma 4 audio, geist engine)
 Speech-to-text into the focused window, fully offline: a streaming
 energy VAD segments utterances, Gemma 4 E2B transcribes them (measured
 4.2% WER English / 7.1% German), ydotool types the result. One static
 binary on the geist inference engine; the model (~3.7 GB) is fetched
 per-user by 'geist-diktat setup'.
EOF

cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = configure ]; then
    udevadm control --reload-rules 2>/dev/null || true
    udevadm trigger /dev/uinput 2>/dev/null || true
    echo "geist-diktat: per user, run 'geist-diktat setup' (downloads ~3.7 GB)."
    echo "Recommended input path: run 'ibus restart', then add the input source"
    echo "'geist-diktat (Diktat)' under Settings -> Keyboard (listed under German)."
    echo "Fallback typing path (ydotool): sudo usermod -aG input \$USER"
fi
EOF
chmod 755 "$STAGE/DEBIAN/postinst"

cat > "$STAGE/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
# Models under ~/.local/share/geist-diktat are user data — kept on purge.
udevadm control --reload-rules 2>/dev/null || true
EOF
chmod 755 "$STAGE/DEBIAN/postrm"

dpkg-deb --root-owner-group --build "$STAGE" "geist-diktat_${VERSION}_${ARCH}.deb"
echo "built: geist-diktat_${VERSION}_${ARCH}.deb"
