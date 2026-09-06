#!/bin/sh
# Real GTK/Qt text widgets under Xvfb. No connection to a host desktop.
set -eu
cd "$(dirname "$0")/.."
APP=${1:?gtk or qt}
case "$APP" in gtk) TITLE=GeistAuditGTK;; qt) TITLE=GeistAuditQt;; *) exit 2;; esac
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/components" "$TMP/cache" "$TMP/config" "$TMP/runtime"
chmod 700 "$TMP/runtime"
sed "s|/usr/libexec/ibus-engine-geist-diktat|$PWD/ibus-engine-geist-diktat-test|" \
    ibus/geist-diktat.xml > "$TMP/components/geist-diktat.xml"
export IBUS_COMPONENT_PATH="$TMP/components" IBUS_ADDRESS="unix:path=$TMP/ibus.sock"
export XDG_CACHE_HOME="$TMP/cache" XDG_CONFIG_HOME="$TMP/config" XDG_RUNTIME_DIR="$TMP/runtime"
export GTK_IM_MODULE=ibus QT_IM_MODULE=ibus XMODIFIERS=@im=ibus
export GEIST_DIKTAT_CMD="${GEIST_DIKTAT_CMD:-sleep 0.3; printf 'Grüße aus dem Toolkit-Test\\n'; sleep 2}"
export IBUS_TEST_EXPECTED="${IBUS_TEST_EXPECTED:-Grüße aus dem Toolkit-Test }"
export AUDIT_APP="$APP" AUDIT_TITLE="$TITLE" AUDIT_OUT="$TMP/output"
timeout "${AUDIT_TIMEOUT:-20}" xvfb-run -a dbus-run-session -- sh -ec '
    ibus-daemon --single --address="$IBUS_ADDRESS" --daemonize
    for i in $(seq 20); do ibus list-engine >/dev/null 2>&1 && break; sleep 0.1; done
    ./build/"$AUDIT_APP"-entry > "$AUDIT_OUT" &
    child=$!
    trap "kill $child 2>/dev/null || true" EXIT
    xdotool search --sync --onlyvisible --name "$AUDIT_TITLE" windowfocus
    sleep 0.5
    # Headless XKB setup may make the setter return nonzero; verify actual
    # global engine state independently before accepting any widget output.
    ibus engine geist-diktat || true
    test "$(ibus engine)" = geist-diktat
    wait "$child"
    cat "$AUDIT_OUT"
    test "$(cat "$AUDIT_OUT")" = "$IBUS_TEST_EXPECTED"
    ibus exit
'
echo "PASS: $APP received Unicode dictation via its IBus input module"
