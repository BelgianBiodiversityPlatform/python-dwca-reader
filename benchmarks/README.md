# Benchmarks

Not part of the test suite. Run manually before and after a change that claims a speedup.

    PYTHONPATH=. .venv/bin/python benchmarks/generate_archive.py /tmp/dwca-bench 400000
    PYTHONPATH=. .venv/bin/python benchmarks/bench_reader.py /tmp/dwca-bench

`generate_archive.py` writes a GBIF-shaped archive: 50 columns, tab separated, no field
enclosure, no header line. 400000 rows is roughly 250MB.

`PYTHONPATH=.` is required because the scripts are run directly (not via `python -m`),
so the repository root is not otherwise on `sys.path` and `import dwca` fails.

## Baseline

Measured on:

- Commit: `771593134599074cc4ff804790065c3519783e51` (branch `parsing-performance`)
- Python: 3.12.0 (CPython)
- Machine: MacBook Pro (Mac14,5, Apple Silicon, arm64), macOS 26.5

Numbers are only comparable within one machine. Command:

    PYTHONPATH=. .venv/bin/python benchmarks/generate_archive.py /tmp/dwca-bench 400000
    PYTHONPATH=. .venv/bin/python benchmarks/bench_reader.py /tmp/dwca-bench

Generator output:

    wrote 400000 rows, 50 columns, 248MB to /tmp/dwca-bench

Benchmark output (second of two consecutive runs; both runs agreed within about 5%):

    archive: /tmp/dwca-bench
      open archive                                    0.24s  n=occurrence.txt  peak=71MB
      iterate, no field access                        9.81s  n=400000  peak=71MB
      iterate + read 14 terms                        10.32s  n=400000  peak=71MB
      random access, ~14k seeks                       0.59s  n=14286  peak=71MB

First run, for comparison (same archive, same process type, run immediately before the one
above):

    archive: /tmp/dwca-bench
      open archive                                    0.46s  n=occurrence.txt  peak=70MB
      iterate, no field access                       10.61s  n=400000  peak=70MB
      iterate + read 14 terms                        10.25s  n=400000  peak=70MB
      random access, ~14k seeks                       0.61s  n=14286  peak=70MB

The "no field access" and "read 14 terms" timings are close to each other in both runs.
This is expected, not a bug: `CoreRow.data` is fully materialized (all columns split and
decoded) when the row is constructed during iteration, so the benchmark's extra `.get()`
calls on an already-built dict add only marginal cost on top of the row-parsing work that
both variants pay. The gap between the two iterate variants is a better indicator of
"reading fields" cost added ON TOP of parsing than a full picture of parsing cost itself,
which the "no field access" line represents.
