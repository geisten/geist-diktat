#!/bin/sh
# Resolve the pinned engine without deleting existing checkouts or model data.
set -eu
: "${GEIST_REPO:?}" "${GEIST_REF:?}" "${GEISTLIB:?}"
stage=''
cleanup() { [ -z "$stage" ] || rm -rf "$stage"; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
resolve() {
    want=$(git -C "$1" rev-parse --quiet --verify "$GEIST_REF^{commit}" || true)
    if [ -z "$want" ]; then
        git -C "$1" fetch --quiet origin "$GEIST_REF"
        want=$(git -C "$1" rev-parse --verify "$GEIST_REF^{commit}")
    fi
    if [ "$(git -C "$1" rev-parse HEAD)" != "$want" ]; then
        # Ordinary checkout refuses conflicting changes. Never force or clean.
        git -C "$1" checkout --quiet --detach "$want"
    fi
}
if [ -e "$GEISTLIB" ] || [ -L "$GEISTLIB" ]; then
    if ! git -C "$GEISTLIB" rev-parse --git-dir >/dev/null 2>&1; then
        echo "engine: existing $GEISTLIB is not a usable Git checkout; preserved unchanged" >&2
        exit 1
    fi
    resolve "$GEISTLIB"
else
    parent=$(dirname "$GEISTLIB")
    mkdir -p "$parent"
    stage=$(mktemp -d "$parent/.geist-engine.XXXXXX")
    git clone --quiet "$GEIST_REPO" "$stage"
    resolve "$stage"
    # Do not mv into a concurrently created checkout.
    if [ -e "$GEISTLIB" ] || [ -L "$GEISTLIB" ]; then
        echo "engine: checkout appeared during preparation; refusing replacement" >&2
        exit 1
    fi
    mv "$stage" "$GEISTLIB"
    stage=''
fi
