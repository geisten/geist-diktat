# Reproducible dictation and adapter benchmarks

```sh
python3 benchmarks/dictation.py --model /path/to/gemma4-e2b-Q4_K_M.gguf \
  --tower /path/to/audio_tower.safetensors --threads 4 --repeats 3 \
  --output benchmarks/results/host-throughput.json
# Same fixture paced as PCM capture would deliver it (20 ms frames):
python3 benchmarks/dictation.py --model /path/to/gemma4-e2b-Q4_K_M.gguf \
  --tower /path/to/audio_tower.safetensors --threads 4 --repeats 3 --paced \
  --output benchmarks/results/host-paced.json
python3 benchmarks/editors.py --output benchmarks/results/host-editors.json
# Linux with the built IBus test binaries and daemon installed:
python3 benchmarks/ibus.py --output benchmarks/results/host-ibus.json
```

Python 3.9+ and Unix `wait4` are required. The runner verifies the project's
exact model and tower SHA-256 **before** inference and records all input and
binary hashes. Each run launches a fresh process. Hashing warms OS caches;
these are **not cold disk-cache measurements**, and the runner never drops
system caches. `--timeout` (default 300 s) kills only the benchmark process
group and records failure. Error exits, missing transcripts and timeouts make
the command fail; WER is reported without a hidden pass threshold.

The default clip is the repository's 9.06 s LibriSpeech utterance. A second
of silence closes the application's VAD. Record CPU/model, RAM, OS, compiler,
thread count, concurrent load and thermal state alongside results.

Metrics:

- `ready_s`: process spawn to the application's “listening” message, including
  model/tower/session initialization.
- `wall_s`: spawn to process exit, including initialization and transcription.
- `processing_s`: wall minus readiness; includes input and VAD silence when paced.
- `wall_rtf`: wall divided by the original clip duration. Below 1 means the
  full file job was faster than the clip duration; it does not promise a
  particular live microphone latency.
- `peak_rss_mib`: individual child `wait4` peak RSS, normalized from bytes on
  macOS and KiB on Linux. Includes resident mmap pages, not total virtual
  allocation, process-tree memory, or total system/swap consumption.
- `first_output_after_fixture_end_s`: paced runs only; completed transcript
  arrival minus scheduled end of the original WAV. Includes VAD/inference
  delay. This is **not time to first token** or latency from a measured human
  acoustic endpoint. The WAV itself may contain trailing silence.
- `wer`: word Levenshtein, lowercase, punctuation removed except apostrophes.
  This tiny English regression sample cannot reproduce the README's corpus
  WER claims, establish German accuracy, or rank competing recognizers.

Three fresh-process repetitions give a descriptive median and range, not a
statistically strong p95/p99. `--paced` models delivery rate through stdin;
microphone drivers, scheduling under real desktop use and acoustic noise are
outside the measurement. The synchronous application can backpressure capture
during decode; a single utterance is not a long-session reliability test.

Editor measurements cover startup plus a **stub transcript** insertion into a
fresh editor. IBus measurements include private daemon startup, a stub Unicode
commit and teardown. Neither is a neural recognition benchmark. Do not add
their medians to ASR figures and claim a measured end-to-end desktop latency.
