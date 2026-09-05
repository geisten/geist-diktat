#!/bin/sh
# sync-engine.sh — put the pinned geistlib engine at $GEISTLIB.
#
# Called from the Makefile while make is still PARSING: the engine's mk/
# fragments are include'd and its detect-target.sh is invoked there, so the
# checkout has to be right before parsing ends. A normal target runs too late —
# make would already have read the previous target-*.mk.
#
# Verifies on every run rather than only cloning when missing. A
# clone-if-missing check leaves the old engine in place after a GEIST_REF bump,
# and that ships as a binary which builds fine and mis-transcribes — the #277
# "deaf binary" class — instead of failing the build.
set -eu

: "${GEIST_REPO:?}" "${GEIST_REF:?}" "${GEISTLIB:?}"

if [ ! -d "$GEISTLIB/.git" ]; then
    echo "engine: cloning $GEIST_REPO -> $GEISTLIB"
    rm -rf "$GEISTLIB"
    git clone --quiet "$GEIST_REPO" "$GEISTLIB"
fi

# Resolve the pin locally; only reach the network when the ref is unknown.
want=$(git -C "$GEISTLIB" rev-parse --quiet --verify "$GEIST_REF^{commit}" || true)
if [ -z "$want" ]; then
    echo "engine: fetching $GEIST_REF"
    git -C "$GEISTLIB" fetch --quiet --tags origin
    want=$(git -C "$GEISTLIB" rev-parse --verify "$GEIST_REF^{commit}")
fi

if [ "$(git -C "$GEISTLIB" rev-parse HEAD)" != "$want" ]; then
    echo "engine: $GEIST_REF -> $(echo "$want" | cut -c1-12)"
    git -C "$GEISTLIB" checkout --quiet --detach "$want"
fi
