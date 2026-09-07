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
case "$VERSION" in ''|*[!0-9A-Za-z.+:~_-]*) echo 'invalid package version' >&2; exit 1;; esac
PROFILE="${GEIST_PACKAGE_PROFILE:-geist}"
case "$PROFILE" in
geist) BINARY=./diktat; CORE_NAME=diktat;;
whisper-small) BINARY=build/whisper-resident/diktat-whisper; CORE_NAME=diktat-whisper;;
*) echo 'invalid package profile' >&2; exit 1;;
esac
ARCH="$(dpkg --print-architecture)"
STAGE="build/geist-diktat_${VERSION}_${ARCH}"

test -x "$BINARY" || { echo "build selected decoder first: $BINARY" >&2; exit 1; }

rm -rf "$STAGE"
mkdir -p \
    "$STAGE/DEBIAN" \
    "$STAGE/usr/bin" \
    "$STAGE/usr/share/geist-diktat" \
    "$STAGE/usr/share/doc/geist-diktat"

python3 packaging/stage-runtime.py "$STAGE/usr" --profile "$PROFILE"
strip "$STAGE/usr/bin/$CORE_NAME"
python3 packaging/stage-runtime.py "$STAGE/usr" --finalize
# IBus engine (built via `make ibus`; required for the .deb).
test -x ./ibus-engine-geist-diktat || { echo "build the ibus engine first (make ibus)" >&2; exit 1; }
mkdir -p "$STAGE/usr/libexec" "$STAGE/usr/share/ibus/component"
install -m755 ibus-engine-geist-diktat "$STAGE/usr/libexec/"
strip "$STAGE/usr/libexec/ibus-engine-geist-diktat"
install -m644 ibus/geist-diktat.xml "$STAGE/usr/share/ibus/component/"
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

if [ "$PROFILE" = whisper-small ]; then
    cat >> "$STAGE/usr/share/doc/geist-diktat/copyright" <<'EOF'

Files: usr/bin/diktat-whisper
Copyright: 2023-2026 The ggml authors
License: MIT
EOF
    # Minimal Ubuntu images exclude ordinary documentation, but retain copyright.
    # Keep the complete linked engine license in that mandatory file too.
    sed -e 's/^$/./' -e 's/^/ /' build/whisper.cpp/LICENSE >> "$STAGE/usr/share/doc/geist-diktat/copyright"
fi

# Derive minimum ABI versions from both actual binaries, including C++/OpenMP.
# Build hosts need dpkg-dev; end-user packages do not.
SHLIB_DEPS=$(python3 packaging/shlib-deps.py "$BINARY" ./ibus-engine-geist-diktat)

INSTALLED_SIZE=$(du -sk "$STAGE" | cut -f1)
cat > "$STAGE/DEBIAN/control" <<EOF
Package: geist-diktat
Version: $VERSION
Architecture: $ARCH
Maintainer: germar <g.schlegel@geisten.net>
Installed-Size: $INSTALLED_SIZE
Depends: $SHLIB_DEPS, alsa-utils, curl, python3
Recommends: ibus
Section: sound
Priority: optional
Homepage: https://github.com/geisten/geist-diktat
Description: local dictation with the $PROFILE model profile
 Local speech recognition with a supervised audio pipeline and an IBus
 input source. Model files are fetched per user with geist-diktat setup.
 Use geist-diktat doctor --verify to inspect the selected configuration.
 The whisper-small profile is a development build for the build host;
 broad CPU compatibility and complete desktop acceptance remain pending.
EOF

# Models under ~/.local/share/geist-diktat are user data; nothing to undo
# on purge, so the package ships no postrm.
cat > "$STAGE/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
if [ "$1" = configure ]; then
    echo "geist-diktat: per user, run 'geist-diktat setup' for its selected model profile."
    echo "If needed, sign out and back in; add the input source 'geist-diktat"
    echo "(Diktat)' under Settings -> Keyboard (listed under German)."
fi
EOF
chmod 755 "$STAGE/DEBIAN/postinst"

dpkg-deb --root-owner-group --build "$STAGE" "geist-diktat_${VERSION}_${ARCH}.deb"
echo "built: geist-diktat_${VERSION}_${ARCH}.deb"
