#!/bin/sh
# Known synthetic speech endpoint -> production supervisor/core/IBus -> widget.
# Only the engine API is a stub. This verifies timing instrumentation, not ASR.
set -eu
cd "$(dirname "$0")/.."
APP=${1:?gtk or qt}
case "$APP" in gtk|qt) ;; *) exit 2;; esac
mkdir -p tests/results build
RUN=$(mktemp -d)
trap 'rm -rf "$RUN"' EXIT
export LATENCY_RUN="$RUN" LATENCY_ROOT="$PWD"
python3 - <<'PY'
import json,os,struct,wave
from pathlib import Path
p=Path(os.environ['LATENCY_RUN'])
with wave.open(str(p/'audio.wav'),'wb') as w:
 w.setparams((1,2,16000,0,'NONE','not compressed'))
 w.writeframes(struct.pack('<h',1000)*8000+bytes(25600))
(p/'annotations.json').write_text(json.dumps([{'output_seq':1,'end_sample':8000}]))
PY
${CC:-cc} -std=c2x -O1 -g -Igeistlib/include tests/core_stub.c -lm -o "$RUN/core"
export GEIST_DIKTAT_TRACE="$PWD/tests/results/$APP-latency-trace.jsonl"
: > "$GEIST_DIKTAT_TRACE"
GEIST_DIKTAT_CMD=$(python3 - <<'PY'
import os,shlex,sys
from pathlib import Path
root=Path(os.environ['LATENCY_ROOT']);p=Path(os.environ['LATENCY_RUN'])
capture=shlex.join([sys.executable,str(root/'benchmarks/trace_capture.py'),str(p/'audio.wav')])
# IBus can reactivate on focus changes while the test window closes. Feed the
# annotated fixture exactly once; an extra activation is not a second session.
print('mkdir '+shlex.quote(str(p/'started'))+' || exit 0; exec '+shlex.join([sys.executable,str(root/'runtime/diktat_runtime.py'),'--capture',capture,'--',str(p/'core'),'model.gguf']))
PY
)
export GEIST_DIKTAT_CMD
export IBUS_TEST_EXPECTED='Hallo Welt Grüße! '
sh tests/toolkit_isolated.sh "$APP"
python3 benchmarks/latency.py --wait-seconds 3 --trace "$GEIST_DIKTAT_TRACE" --annotations "$RUN/annotations.json" \
    --output "tests/results/$APP-latency.json"
