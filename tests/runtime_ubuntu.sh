#!/bin/sh
# Use stock ubuntu:24.04, mount build/ubuntu-package read-only at /packages.
set -eu
test -f /.dockerenv || exit 2
export DEBIAN_FRONTEND=noninteractive
apt-get update -q
apt-get install -y -q /packages/geist-diktat_*.deb
set +e
geist-diktat >/tmp/diktat-usage 2>&1
status=$?
set -e
test "$status" = 2
grep -q usage /tmp/diktat-usage
set +e
diktat /nonexistent.gguf </dev/null >/tmp/diktat-missing 2>&1
status=$?
set -e
test "$status" = 1
grep -q 'model_load failed' /tmp/diktat-missing
command -v arecord
command -v curl
command -v python3
command -v ibus-daemon
test -x /usr/libexec/ibus-engine-geist-diktat
test -f /usr/share/ibus/component/geist-diktat.xml
ldd /usr/bin/diktat
echo 'PASS: declared package dependencies work in stock Ubuntu 24.04'
