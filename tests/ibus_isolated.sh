#!/bin/sh
# Private registry and private D-Bus; never restart the user's live IBus.
set -eu
cd "$(dirname "$0")/.."
command -v ibus-daemon >/dev/null || { echo 'SKIP: ibus-daemon missing'; exit 77; }
command -v dbus-run-session >/dev/null || { echo 'SKIP: dbus-run-session missing'; exit 77; }
test -x ./ibus-engine-geist-diktat-test
test -x ./ibus-test-client
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/components" "$TMP/cache" "$TMP/config"
sed "s|/usr/libexec/ibus-engine-geist-diktat|$PWD/ibus-engine-geist-diktat-test|" \
    ibus/geist-diktat.xml > "$TMP/components/geist-diktat.xml"
export IBUS_COMPONENT_PATH="$TMP/components"
export XDG_CACHE_HOME="$TMP/cache" XDG_CONFIG_HOME="$TMP/config"
export IBUS_ADDRESS="unix:path=$TMP/ibus.sock"
export GEIST_DIKTAT_CMD="${GEIST_DIKTAT_CMD:-printf 'Grüße aus dem IBus-Test\\n'; sleep 2}"
export IBUS_TEST_EXPECTED="${IBUS_TEST_EXPECTED:-Grüße aus dem IBus-Test }"
dbus-run-session -- sh -ec '
    ibus-daemon --single --address="$IBUS_ADDRESS" --daemonize
    for i in $(seq 20); do ibus list-engine >/dev/null 2>&1 && break; sleep 0.1; done
    ibus list-engine | grep -q geist-diktat
    OUT=$(timeout 15 ./ibus-test-client)
    printf "%s\n" "$OUT"
    test "$OUT" = "$IBUS_TEST_EXPECTED"
    if [ -x ./build/ibus-privacy ]; then ./build/ibus-privacy; fi
    ibus exit
'
echo 'PASS: isolated IBus registration and Unicode commit'
