# geist-diktat — system-wide local dictation on the geist engine.
#
# The engine is pinned by GEIST_REF below and checked out into $(GEISTLIB) by
# scripts/sync-engine.sh — no git submodule. Every make run verifies the
# checkout against the pin, so bumping GEIST_REF takes effect on the next
# build; there is no second command to remember and no stale-engine window.
#
# Platform knowledge stays in geistlib: its detect-target.sh picks the target
# and its mk/ fragments supply the flags, so diktat links with exactly what the
# engine was built with.
#
# `#>` lines below are what `make help` prints — the one place that lists
# every entry point, so CI calls these targets instead of the scripts.
#
#> make               build ./diktat (syncs + builds libgeist.a on demand)
#> make ibus          IBus engine + test client (Linux, libibus-1.0-dev)
#> make setup         fetch model (~3.1 GB) + audio tower (~590 MB), SHA-pinned
#>
#> make test          smoke test (full transcript check when fixtures exist)
#> make test-audit    model-free contract suite (tests/test_*.py)
#> make test-nvim     headless Neovim plugin test (diktat stubbed)
#> make test-ibus     headless IBus daemon+engine+client integration
#> make test-e2e      real model + real audio, WER-gated (needs fixtures)
#> make test-ubuntu   container suite: real GTK3/Qt5/IBus under Xvfb
#> make coverage      LLVM source coverage of src/diktat.c
#>
#> make deb           .deb via packaging/build-deb.sh      (VERSION=x.y.z)
#> make tarball       tar.gz via packaging/build-tarball.sh (VERSION=x.y.z)
#> make format        clang-format, shared style file with the engine
#> make clean         drop the binaries; distclean also drops the engine
#>
#> make GEIST_REF=... build against another engine revision, one-off

GEIST_REPO ?= https://github.com/geisten/geistlib.git
GEIST_REF  ?= bb751c596f7d6ed3f73fa2d4c4e29e617cada57f
GEISTLIB   ?= geistlib
MODE       ?= release

# Parse-time, not a target: the include directives and detect-target.sh below
# are evaluated while make is still reading this file. Skipped for goals that
# do not need an engine, so a fresh `make clean` does not clone 14 MB and an
# ibus-only build needs no git in its container.
# The ibus binaries compile against libibus only — no libgeist, no engine.
NO_ENGINE := clean distclean help format test-nvim test-ibus deb tarball \
             ibus ibus-engine-geist-diktat \
             ibus-engine-geist-diktat-test ibus-test-client
ifneq (,$(filter-out $(NO_ENGINE),$(or $(MAKECMDGOALS),all)))

ENGINE := $(shell GEIST_REPO='$(GEIST_REPO)' GEIST_REF='$(GEIST_REF)' \
                  GEISTLIB='$(GEISTLIB)' sh scripts/sync-engine.sh >&2 && echo ok)
ifneq ($(ENGINE),ok)
$(error engine sync failed — see the messages above)
endif

TARGET ?= $(shell $(GEISTLIB)/mk/detect-target.sh)
include $(GEISTLIB)/mk/target-$(TARGET).mk

GEMM_PROVIDER ?= native
include $(GEISTLIB)/mk/gemm-$(GEMM_PROVIDER).mk

endif

LIB := $(GEISTLIB)/lib/$(TARGET)/$(MODE)/libgeist.a

# EXTRA_* are geistlib's own escape hatches (mk/common.mk); same names here so
# one convention covers both. The Linux release tarball links with
# EXTRA_LDFLAGS=-static against musl — geistlib deliberately keeps -static out
# of its archive build, because link flags belong to whoever links.
CFLAGS  := -std=c23 -O2 -Wall -Wextra -I$(GEISTLIB)/include $(CFLAGS_TARGET) $(GEMM_CFLAGS) $(EXTRA_CFLAGS)
LDFLAGS := $(LDFLAGS_TARGET) $(EXTRA_LDFLAGS)
LDLIBS  := $(LDLIBS_TARGET) $(GEMM_LDLIBS) $(EXTRA_LDLIBS)


.PHONY: all help setup test test-audit test-nvim test-ibus test-e2e \
        test-ubuntu coverage \
        deb tarball format ibus clean distclean

all: diktat

# `make help` was already engine-free (NO_ENGINE) but had no recipe.
# This file only: $(MAKEFILE_LIST) also holds the engine's mk/ fragments.
help:
	@grep "^#>" Makefile | cut -c4-

diktat: src/diktat.c $(LIB)
	$(CC) $(CFLAGS) -o $@ $< $(LIB) $(LDFLAGS) $(LDLIBS)

# IBus engine + headless test client (Linux with libibus-1.0-dev only).
IBUS_CFLAGS := -std=c23 -O2 -Wall -Wextra $(shell pkg-config --cflags ibus-1.0 2>/dev/null)
IBUS_LIBS   := $(shell pkg-config --libs ibus-1.0 2>/dev/null)

ibus: ibus-engine-geist-diktat ibus-engine-geist-diktat-test ibus-test-client

ibus-engine-geist-diktat: ibus/engine.c
	$(CC) $(IBUS_CFLAGS) -o $@ $< $(IBUS_LIBS)

# Same engine with the GEIST_DIKTAT_CMD pipeline override compiled in.
# Separate binary, not a flag on the one above: the packaged engine must
# never take its command line from the environment, and one output per
# set of flags keeps a stale object from leaking the hook into a release.
ibus-engine-geist-diktat-test: ibus/engine.c
	$(CC) $(IBUS_CFLAGS) -DGEIST_DIKTAT_TEST_HOOKS -o $@ $< $(IBUS_LIBS)

ibus-test-client: ibus/test_client.c
	$(CC) $(IBUS_CFLAGS) -o $@ $< $(IBUS_LIBS)

# Always delegate: the submodule's own make is incremental and cheap,
# and a plain file target went stale on submodule bumps (the lib exists
# but is outdated — measured: a deaf binary after the #277 pin bump).
$(LIB): FORCE
	$(MAKE) -C $(GEISTLIB) lib TARGET=$(TARGET) MODE=$(MODE)

FORCE:

# Model + tower land inside the submodule (gguf_artifacts/, audio_bench/)
# where the engine's default search paths find them. Idempotent: both are
# real file targets in geistlib's Makefile.
setup:
	$(MAKE) -C $(GEISTLIB) fetch-model fetch-audio-tower

test: diktat
	sh tests/smoke.sh

# Detailed model-free contracts; exposes the findings in doc/AUDIT-2026-09-05.md.
test-audit:
	CC="$(CC)" python3 -m unittest discover -s tests -p 'test_*.py' -v

test-nvim:
	sh tests/nvim_smoke.sh

test-ibus: ibus
	sh tests/ibus_smoke.sh

# The one test that hears: real model + real audio, scored against a
# reference transcript. Fixtures are 3.7 GB, so this is nightly-only.
test-e2e: diktat
	sh tests/e2e_wer.sh

# The disposable-container suite: contracts + real GTK3/Qt5/IBus under Xvfb.
# Needs tests/ubuntu.Dockerfile's toolchain, so it is CI/container-only.
test-ubuntu:
	sh tests/ubuntu.sh

# LLVM source coverage of src/diktat.c through tests/core_stub.c.
coverage:
	sh tests/coverage.sh

# Packaging only packages — it does not decide how the binary was built.
# No prerequisite on diktat and no engine sync (NO_ENGINE): re-entering the
# build here would re-detect TARGET and pick up target-linux.mk's
# `GEMM_PROVIDER ?= openblas`, silently packaging a differently-linked
# binary than the build step produced. Build first, then package; both
# scripts assert `test -x ./diktat` themselves. VERSION passes through.
deb:
	sh packaging/build-deb.sh

tarball:
	sh packaging/build-tarball.sh

# Same style file as the engine, so a function moved between repos does not
# reformat. ibus/engine.c is GLib-shaped C and reformats too — that is fine,
# the style file is the tie-breaker, not the GLib house style.
format:
	clang-format -i src/*.c ibus/*.c tests/*.c tests/*.cpp

clean:
	rm -f diktat ibus-engine-geist-diktat ibus-engine-geist-diktat-test ibus-test-client

# The engine checkout is build input, not source: distclean drops it so the
# next build re-clones at the pin.
distclean: clean
	rm -rf $(GEISTLIB)
