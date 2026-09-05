#!/bin/sh
# Designed for the disposable image in ubuntu.Dockerfile.
set -u
mkdir -p tests/results build
export CC=gcc-14
export VIM_BINARY=/usr/bin/vim.basic
python3 -m unittest discover -s tests -p 'test_*.py' -v > tests/results/ubuntu-contracts.log 2>&1
contracts=$?
make CC=gcc-14 TARGET=linux GEMM_PROVIDER=native ibus > tests/results/ubuntu-ibus-build.log 2>&1 || exit 1
gcc-14 -std=c2x -O1 -g $(pkg-config --cflags ibus-1.0) tests/ibus_lifecycle.c \
    $(pkg-config --libs ibus-1.0) -o build/ibus-lifecycle || exit 1
build/ibus-lifecycle > tests/results/ubuntu-ibus-lifecycle.log 2>&1
lifecycle=$?
gcc-14 -std=c2x -O1 -g $(pkg-config --cflags ibus-1.0) tests/ibus_privacy.c \
    $(pkg-config --libs ibus-1.0) -o build/ibus-privacy || exit 1
sh tests/ibus_isolated.sh > tests/results/ubuntu-ibus-integration.log 2>&1
integration=$?
gcc-14 $(pkg-config --cflags gtk+-3.0) tests/gtk_entry.c $(pkg-config --libs gtk+-3.0) -o build/gtk-entry || exit 1
g++ -fPIC $(pkg-config --cflags Qt5Widgets) tests/qt_entry.cpp $(pkg-config --libs Qt5Widgets) -o build/qt-entry || exit 1
sh tests/toolkit_isolated.sh gtk > tests/results/ubuntu-gtk.log 2>&1
gtk=$?
sh tests/toolkit_isolated.sh qt > tests/results/ubuntu-qt.log 2>&1
qt=$?
printf 'contracts=%s lifecycle=%s integration=%s gtk=%s qt=%s\n' "$contracts" "$lifecycle" "$integration" "$gtk" "$qt"
test "$contracts$lifecycle$integration$gtk$qt" = 00000
