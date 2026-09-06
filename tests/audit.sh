#!/bin/sh
# Provision the pinned engine headers with `make` first on a fresh checkout.
set -eu
cd "$(dirname "$0")/.."
exec python3 -m unittest discover -s tests -p 'test_*.py' -v
