#!/bin/sh
# LLVM source coverage of the actual C dictation wrapper with fake engine API.
# Known regressions keep the test exit status nonzero; coverage still exports.
set -u
cd "$(dirname "$0")/.."
mkdir -p build/coverage tests/results
export GEIST_TEST_COVERAGE_DIR="$PWD/build/coverage"
export LLVM_PROFILE_FILE="$GEIST_TEST_COVERAGE_DIR/core-%p.profraw"
# Isolate each invocation from earlier profiles rather than merge stale runs.
run_dir=$(mktemp -d "$GEIST_TEST_COVERAGE_DIR/run.XXXXXX")
export LLVM_PROFILE_FILE="$run_dir/core-%p.profraw"
python3 -m unittest discover -s tests -p test_core.py -v > tests/results/core-coverage-tests.log 2>&1
status=$?
if [ "$(uname -s)" = Darwin ]; then
    profdata=$(xcrun --find llvm-profdata); cov=$(xcrun --find llvm-cov)
else
    profdata=${LLVM_PROFDATA:-llvm-profdata}; cov=${LLVM_COV:-llvm-cov}
fi
"$profdata" merge -sparse "$run_dir"/*.profraw -o "$run_dir/core.profdata" || exit 2
"$cov" report build/coverage/core-stub -instr-profile="$run_dir/core.profdata" src/diktat.c > tests/results/core-coverage.txt || exit 2
"$cov" export build/coverage/core-stub -instr-profile="$run_dir/core.profdata" src/diktat.c > tests/results/core-coverage.json || exit 2
cat tests/results/core-coverage.txt
exit "$status"
