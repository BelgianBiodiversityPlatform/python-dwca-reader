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
            return sum(
                1 for i in range(0, 100000, 7) if data_file.get_row_by_position(i)
            )

    print("archive:", archive_path)
    timed("open archive", open_and_close)
    timed("iterate, no field access", lambda: iterate(False))
    timed("iterate + read 14 terms", lambda: iterate(True))
    timed("random access, ~14k seeks", random_access)


if __name__ == "__main__":
    main(sys.argv[1])
