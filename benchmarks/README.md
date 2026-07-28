# Benchmarks

Not part of the test suite. Run manually before and after a change that claims a speedup.

    PYTHONPATH=. .venv/bin/python benchmarks/generate_archive.py /tmp/dwca-bench 400000
    PYTHONPATH=. .venv/bin/python benchmarks/bench_reader.py /tmp/dwca-bench

`generate_archive.py` writes a GBIF-shaped archive: 50 columns, tab separated, no field
enclosure, no header line. 400000 rows is roughly 250MB. Because `fieldsEnclosedBy=""`,
only the unquoted parsing path (the `line.rstrip(...).split(...)` branch of
`CSVDataFile._iter_field_lists()` in `dwca/files.py`) is exercised by these benchmarks - the
quoted-field path is not measured here.

`PYTHONPATH=.` is required because the scripts are run directly (not via `python -m`),
so the repository root is not otherwise on `sys.path` and `import dwca` fails.

The `peak=` column comes from `resource.getrusage(...).ru_maxrss`, which is a process-wide
high-water mark, not a per-measurement figure: it never decreases within a run, so each
`timed()` line reports the peak RSS seen so far across the whole process, including
everything measured by earlier lines. Compare `peak=` across separate invocations of the
script, not across lines of the same run.

The "open archive" timing is the only one that isolates archive-opening cost: "iterate,
..." and "random access, ..." both open a fresh `DwCAReader` (via `with DwCAReader(...)`)
inside the timed region, so their reported time includes opening the archive (parsing the
metafile and building the core file's line-offset index) on top of the operation the label
describes.

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

## After the streaming engine

Measured on:

- Commit: `c48124009f02fa24b0d5b3f853036f7b8f302f0a` (branch `parsing-performance`)
- Python: 3.12.0 (CPython)
- Machine: MacBook Pro (Mac14,5, Apple Silicon, arm64), macOS 26.5

The Phase 0 baseline above was recorded in a separate session. Machine variance between
sessions has been observed to be as large as ~40 percent on identical code, so it is not a
trustworthy comparison by itself. To get an honest pair, both sides below were re-measured
back to back, in one sitting, on an otherwise idle machine: the Phase 0 starting commit
(`fd829b6`, checked out into a scratch worktree) immediately followed by the current commit
above, against the same generated archive.

Generator output (shared by both sides):

    wrote 400000 rows, 50 columns, 248MB to /tmp/dwca-bench

Before (commit `fd829b61962b5a813705a0f7c5d1f12c1efe07e7`, run 1 of 2):

    archive: /tmp/dwca-bench
      open archive                                    0.23s  n=occurrence.txt  peak=73MB
      iterate, no field access                        6.76s  n=400000  peak=73MB
      iterate + read 14 terms                         6.84s  n=400000  peak=73MB
      random access, every 7th row up to 100k         0.40s  n=14286  peak=73MB

Before, run 2 of 2 (same archive, same process type, run immediately after):

    archive: /tmp/dwca-bench
      open archive                                    0.16s  n=occurrence.txt  peak=71MB
      iterate, no field access                        6.80s  n=400000  peak=71MB
      iterate + read 14 terms                         6.88s  n=400000  peak=71MB
      random access, every 7th row up to 100k         0.38s  n=14286  peak=71MB

After (commit `c48124009f02fa24b0d5b3f853036f7b8f302f0a`, run 1 of 2, measured immediately
after the "before" runs, same archive):

    archive: /tmp/dwca-bench
      open archive                                    0.00s  n=occurrence.txt  peak=67MB
      iterate, no field access                        1.65s  n=400000  peak=67MB
      iterate + read 14 terms                         1.74s  n=400000  peak=67MB
      random access, every 7th row up to 100k         0.26s  n=14286  peak=79MB

After, run 2 of 2:

    archive: /tmp/dwca-bench
      open archive                                    0.00s  n=occurrence.txt  peak=67MB
      iterate, no field access                        1.68s  n=400000  peak=67MB
      iterate + read 14 terms                         1.79s  n=400000  peak=67MB
      random access, every 7th row up to 100k         0.19s  n=14286  peak=76MB

Both sides are consistent run to run (within a few percent). Using the average of the two
runs on each side:

- `open archive`: 0.20s -> 0.00s (below the timer's resolution; opening no longer scans the
  data file to build the line offset index, it is now built lazily on first positional
  access).
- `iterate, no field access`: 6.78s -> 1.67s, roughly 4.1x faster.
- `iterate + read 14 terms`: 6.86s -> 1.77s, roughly 3.9x faster (range 3.8x-4.0x across the
  two run pairs). This is the headline number: it clears the phase's 2.5x target by a wide
  margin.
- `random access, every 7th row up to 100k`: 0.39s -> 0.23s, roughly 1.7x faster.

`peak=` rose slightly on the "after" random access line (79MB / 76MB vs 67MB elsewhere in
the same runs) because that is the first operation in the process that builds the line
offset index; it remains well below the "before" side's peak, where the index was built
eagerly on open.

The absolute timings above are not comparable across sessions - only the ratio between two
runs measured back to back in the same sitting is. Confirmed later: the same two commits
(`fd829b6` and `c481240`) that recorded `iterate + read 14 terms` at 6.86s and 1.77s here
measured 9.34s and 2.50s on a later, busier session on the same machine - the absolute
numbers moved by roughly a third, but the ratio held (3.7x-4.0x measured back to back that
time, against 3.8x-4.0x recorded above). Do not read the absolute seconds as a target or a
regression signal in isolation; re-measure both sides back to back before drawing any
conclusion from them.

## iter_terms

`DwCAReader.iter_terms()` / `CSVDataFile.iter_terms()` skip building both the `Row` object
and its term-to-value dict, yielding a plain tuple of the requested terms per row instead.
Measured against the row API on the same 400000-row, 50-column archive generated above
(`/tmp/dwca-bench`), reading 14 terms per row in both cases, both paths measured back to
back in one run (rerun twice to check consistency):

    # Row path
    with DwCAReader(ARCHIVE, skip_metadata=True) as dwca:
        for row in dwca:
            data = row.data
            for term in TERMS:
                data.get(term)

    # iter_terms path
    with DwCAReader(ARCHIVE, skip_metadata=True) as dwca:
        for values in dwca.iter_terms(TERMS):
            pass

Run 1:

    rows path      2.86s
    iter_terms     0.98s
    ratio (rows/iter_terms): 2.93x

Run 2 (immediately after, same process type):

    rows path      2.13s
    iter_terms     0.75s
    ratio (rows/iter_terms): 2.85x

Run 3:

    rows path      2.12s
    iter_terms     0.72s
    ratio (rows/iter_terms): 2.95x

Consistent at roughly 2.85x-2.95x across three back-to-back runs, comfortably above the
"roughly half the rows path" (2x) expectation. As with the numbers above, absolute seconds
vary by session; only the ratio, measured back to back, is meaningful.
