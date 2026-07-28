"""Time the documented read paths against a generated archive.

Usage:
    python benchmarks/generate_archive.py /tmp/dwca-bench 400000
    python benchmarks/bench_reader.py /tmp/dwca-bench

Record the output before and after a change: this is the evidence for any speedup claim.
"""

import resource
import sys
import time

from dwca.read import DwCAReader

# A subset a real consumer reads, rather than every column.
WANTED = [
    "http://rs.tdwg.org/dwc/terms/" + name
    for name in (
        "occurrenceID scientificName basisOfRecord kingdom family genus country "
        "locality decimalLatitude decimalLongitude year month day recordedBy"
    ).split()
]


def peak_memory_mb():
    usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Linux reports kilobytes, macOS reports bytes.
    if sys.platform == "darwin":
        usage = usage / 1024
    return usage / 1024


def timed(label, function):
    started = time.perf_counter()
    count = function()
    elapsed = time.perf_counter() - started
    print(
        "  {label:44s} {elapsed:7.2f}s  n={count}  peak={memory:.0f}MB".format(
            label=label, elapsed=elapsed, count=count, memory=peak_memory_mb()
        )
    )


def main(archive_path):
    def open_and_close():
        reader = DwCAReader(archive_path, skip_metadata=True)
        location = reader.core_file_location
        reader.close()
        return location

    def iterate(read_fields):
        count = 0
        with DwCAReader(archive_path, skip_metadata=True) as reader:
            for row in reader:
                if read_fields:
                    data = row.data
                    for term in WANTED:
                        data.get(term)
                count += 1
        return count

    def random_access():
        with DwCAReader(archive_path, skip_metadata=True) as reader:
            data_file = reader.core_file
            # No public API exposes the row count. _line_offsets is already built when the
            # CSVDataFile is opened (that's the whole point of the index), so reading its
            # length here is free and lets the range below scale with the actual archive
            # instead of hardcoding 100000 (which raises IndexError on smaller archives).
            row_count = len(data_file._line_offsets) - data_file.lines_to_ignore
            upper_bound = min(row_count, 100000)
            return sum(
                1
                for i in range(0, upper_bound, 7)
                if data_file.get_row_by_position(i)
            )

    print("archive:", archive_path)
    timed("open archive", open_and_close)
    timed("iterate, no field access", lambda: iterate(False))
    timed("iterate + read 14 terms", lambda: iterate(True))
    timed("random access, every 7th row up to 100k", random_access)


if __name__ == "__main__":
    main(sys.argv[1])
