# geist-diktat — system-wide local dictation on the geist engine.
#
# geistlib is a pinned submodule; this Makefile mirrors geistlib's own
# examples/Makefile so diktat links with exactly the flags the engine
# was built with — no duplicated platform knowledge.
#
#   make            # build ./diktat (builds the pinned libgeist.a on demand)
#   make setup      # fetch model (~3.1 GB) + audio tower (~590 MB), SHA-pinned
#   make test       # smoke test (full transcript check when fixtures exist)

GEISTLIB := geistlib
TARGET ?= $(shell $(GEISTLIB)/mk/detect-target.sh)
MODE   ?= release

include $(GEISTLIB)/mk/target-$(TARGET).mk

GEMM_PROVIDER ?= native
include $(GEISTLIB)/mk/gemm-$(GEMM_PROVIDER).mk

LIB := $(GEISTLIB)/lib/$(TARGET)/$(MODE)/libgeist.a

CFLAGS  := -std=c23 -O2 -Wall -Wextra -I$(GEISTLIB)/include $(CFLAGS_TARGET) $(GEMM_CFLAGS)
LDFLAGS := $(LDFLAGS_TARGET)
LDLIBS  := $(LDLIBS_TARGET) $(GEMM_LDLIBS)


.PHONY: all setup test ibus clean

all: diktat

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

clean:
	rm -f diktat ibus-engine-geist-diktat ibus-engine-geist-diktat-test ibus-test-client
