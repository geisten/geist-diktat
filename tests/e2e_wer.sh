#!/bin/sh
# e2e_wer.sh — the real model must HEAR (#8).
#
# Pipes the LibriSpeech fixture through ./diktat with the real model +
# audio tower and scores the transcript against the reference (word-level
# Levenshtein, standard ASR normalization). Threshold 15 % on this clip —
# the healthy engine measures 0 %; the #270-class injection bug measured
# 77 %+, so anything near the threshold is a real regression.
#
# Fixtures: $GEIST_DIKTAT_DATA (default ~/.local/share/geist-diktat)
# holding gemma4-e2b-Q4_K_M.gguf + audio_tower.safetensors. SKIPs when
# absent — the nightly workflow provisions them via cache.
set -e
cd "$(dirname "$0")/.."

DATA="${GEIST_DIKTAT_DATA:-${XDG_DATA_HOME:-$HOME/.local/share}/geist-diktat}"
MODEL="$DATA/gemma4-e2b-Q4_K_M.gguf"
TOWER="$DATA/audio_tower.safetensors"
WAV=tests/fixtures/librispeech-1089-134691-0016.wav
REF=tests/fixtures/librispeech-1089-134691-0016.txt
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

test -x ./diktat || { echo "FAIL: ./diktat not built"; exit 1; }
[ -f "$MODEL" ] || { echo "SKIP: model not present ($MODEL)"; exit 0; }
[ -f "$TOWER" ] || { echo "SKIP: audio tower not present ($TOWER)"; exit 0; }

export GEIST_AUDIO_MODEL_PATH="$TOWER"
export GEIST_MEL_CONSTANTS_PATH=geistlib/audio_test_data/mel_constants.bin

# WAV data + a second of silence so the VAD closes the utterance.
# python's wave module walks the RIFF chunks — no fixed-offset assumption
# (the #269 bug class).
(
    python3 -c "import sys, wave; w = wave.open(sys.argv[1]); sys.stdout.buffer.write(w.readframes(w.getnframes()))" "$WAV"
    dd if=/dev/zero bs=32000 count=1 2>/dev/null
) | ./diktat "$MODEL" >"$TMP/transcript.txt" 2>"$TMP/err.txt" || {
    echo "FAIL: diktat pipeline errored:"
    tail -5 "$TMP/err.txt"
    exit 1
}

HYP=$(cat "$TMP/transcript.txt")
echo "transcript: $HYP"
[ -n "$HYP" ] || { echo "FAIL: empty transcript"; exit 1; }

python3 - "$REF" "$TMP/transcript.txt" <<'EOF'
import re
import sys

def norm(text):
    return re.sub(r"[^\w' ]+", " ", text.lower()).split()

ref = norm(open(sys.argv[1]).read())
hyp = norm(open(sys.argv[2]).read())

prev = list(range(len(hyp) + 1))
for i, r in enumerate(ref, 1):
    cur = [i]
    for j, h in enumerate(hyp, 1):
        cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h)))
    prev = cur
wer = prev[-1] / len(ref)
print(f"WER: {wer:.1%} ({prev[-1]} errors / {len(ref)} words)")
sys.exit(0 if wer <= 0.15 else 1)
EOF
echo "PASS"
