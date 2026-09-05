#!/bin/sh
# build-linux.sh — the release-grade Linux build of diktat + the IBus engine.
#
# Exists because ci.yml and release.yml need byte-identical builds: what CI
# proves per PR must be what the tag ships. It was 25 duplicated YAML lines in
# two workflows before, which is the shape that drifts.
#
# arm64 builds in debian:12 with clang-19: the Pi world runs RasPiOS bookworm
# (glibc 2.36); ubuntu-24.04 binaries link libmvec + GLIBC_2.38+ symbols and
# die there (measured on a Pi 5). amd64 stays on the runner's gcc-14 —
# clang-19 backend-crashes on the x86 VNNI kernels, and x86 desktops run
# ubuntu 24.04+ / debian 13+ anyway.
#
# Not a make target: the arm64 half runs make *inside* a container against the
# mounted tree, and make-invoking-docker-invoking-make is the thing you decode
# at 3am. The Makefile's `deb`/`tarball` targets are the normal entry points.
set -eu
cd "$(dirname "$0")/.."

if [ "$(uname -m)" = aarch64 ]; then
    docker run --rm -v "$PWD:/w" -w /w debian:12 bash -ec '
      export DEBIAN_FRONTEND=noninteractive
      apt-get update -q >/dev/null
      # git + ca-certificates: the engine is cloned by the build itself now
      # (GEIST_REF), and this build runs inside the container.
      apt-get install -y -q clang-19 libomp-19-dev libibus-1.0-dev make pkg-config \
                            git ca-certificates >/dev/null
      make CC=clang-19 TARGET=linux GEMM_PROVIDER=native
      make CC=clang-19 GEMM_PROVIDER=native ibus-engine-geist-diktat
    '
else
    make CC=gcc-14 TARGET=linux GEMM_PROVIDER=native
    make CC=gcc-14 GEMM_PROVIDER=native ibus-engine-geist-diktat
fi
