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

T0=$(date +%s)

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

# Scoring belongs to the engine: geistlib/tools/eval_audio_wer.py owns the
# normalization and the word-level Levenshtein, including a fix this repo's
# own copy never had — an ASCII-only character class split "schön" into
# "sch n" and wrecked non-English WER.
#
# Its input is bench_audio_wer's TSV, so one clip's worth is built here.
# diktat reports neither an attach/decode split nor a token count, so those
# columns carry the wall clock and zeros: the tok/s line it prints is
# therefore meaningless, and only the aggregate WER gates this test.
SCORER=geistlib/tools/eval_audio_wer.py
[ -f "$SCORER" ] || { echo "FAIL: $SCORER missing (it ships with the pinned engine)"; exit 1; }

ELAPSED_MS=$(( ($(date +%s) - T0) * 1000 ))
[ "$ELAPSED_MS" -gt 0 ] || ELAPSED_MS=1   # the scorer divides by this

printf '%s\t%s\n' "$WAV" "$(tr '\n' ' ' < "$REF")" > "$TMP/refs.tsv"
printf 'WER\t%s\t0\t%s\t0\t%s\n' "$WAV" "$ELAPSED_MS" "$HYP" > "$TMP/hyps.tsv"

# Not piped into tee: /bin/sh has no pipefail, so set -e would only see tee
# and a crashed scorer would slip through as an empty WER.
python3 "$SCORER" "$TMP/hyps.tsv" "$TMP/refs.tsv" > "$TMP/score.txt"
cat "$TMP/score.txt"

WER=$(sed -n 's/.*aggregate WER: \([0-9.]*\)%.*/\1/p' "$TMP/score.txt")
[ -n "$WER" ] || { echo "FAIL: no aggregate WER in the scorer output"; exit 1; }
awk -v w="$WER" 'BEGIN { exit (w <= 15.0) ? 0 : 1 }' || {
    echo "FAIL: WER ${WER}% is over the 15% threshold"
    exit 1
}
echo "PASS"
