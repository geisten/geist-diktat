#!/bin/sh
# ibus_smoke.sh — headless IBus integration test (#3).
#
# Exercises the REAL production path: the component XML is installed
# into the daemon's search path, ibus-daemon spawns the engine itself
# (--ibus mode), the test client selects the engine and must receive the
# stubbed transcript as a committed text. Dynamic self-registration is
# NOT used here — it does not surface in `ibus list-engine` (measured;
# the standalone mode remains a dev convenience only).
#
# Needs write access to /usr/share/ibus/component (root in CI/container).
# SKIPs when the ibus toolchain is absent.
set -e
cd "$(dirname "$0")/.."

command -v ibus-daemon >/dev/null || { echo "SKIP: ibus-daemon not installed"; exit 0; }
command -v dbus-run-session >/dev/null || { echo "SKIP: dbus-run-session not installed"; exit 0; }
test -x ./ibus-engine-geist-diktat-test || { echo "SKIP: engine not built (make ibus)"; exit 0; }

COMP_DIR=/usr/share/ibus/component
TMP=$(mktemp -d)
SUDO=""
[ -w "$COMP_DIR" ] || SUDO="sudo"
$SUDO mkdir -p "$COMP_DIR" || { echo "SKIP: cannot write $COMP_DIR"; exit 0; }

# Component XML pointing at the just-built engine, in daemon-spawn mode.
# GEIST_DIKTAT_CMD only exists in the -test build (see Makefile).
sed "s|/usr/libexec/ibus-engine-geist-diktat|$(pwd)/ibus-engine-geist-diktat-test|" \
    ibus/geist-diktat.xml >"$TMP/geist-diktat.xml"
$SUDO cp "$TMP/geist-diktat.xml" "$COMP_DIR/geist-diktat.xml"
trap '$SUDO rm -f "$COMP_DIR/geist-diktat.xml"; rm -rf "$TMP"' EXIT

# The daemon spawns the engine and passes its environment down — the
# stub reaches the engine through it.
export GEIST_DIKTAT_CMD='printf "hallo welt\n"; sleep 30'

dbus-run-session -- sh -ec '
    ibus-daemon --panel disable --daemonize
    for i in $(seq 20); do ibus list-engine >/dev/null 2>&1 && break; sleep 0.5; done

    ibus list-engine 2>/dev/null | grep -q geist-diktat || { echo "FAIL: engine not in component list"; exit 1; }
    echo "ok: component registered"

    OUT=$(./ibus-test-client)
    echo "committed: $OUT"
    echo "$OUT" | grep -q "hallo welt" || { echo "FAIL: commit mismatch"; exit 1; }

    # The engine (daemon-spawned) and its stub pipeline must die with the session.
'
sleep 1
if pgrep -f "ibus-engine-geist-diktat" >/dev/null; then
    echo "FAIL: engine outlived the ibus session"
    exit 1
fi
if pgrep -f "sleep 30" >/dev/null; then
    echo "FAIL: pipeline outlived the engine"
    exit 1
fi
echo PASS
