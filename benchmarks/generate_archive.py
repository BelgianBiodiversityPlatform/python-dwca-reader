"""Generate a large, GBIF-shaped Darwin Core Archive for benchmarking.

Usage:
    python benchmarks/generate_archive.py /tmp/bench-archive 400000
"""

import os
import sys

TERMS = (
    ["http://rs.tdwg.org/dwc/terms/occurrenceID"]
    + ["http://rs.gbif.org/terms/1.0/gbifID"]
    + [
        "http://rs.tdwg.org/dwc/terms/" + name
        for name in (
            "datasetName basisOfRecord scientificName scientificNameAuthorship taxonID "
            "kingdom phylum class order family genus specificEpithet taxonRank "
            "countryCode country stateProvince county locality municipality "
            "decimalLatitude decimalLongitude coordinateUncertaintyInMeters "
            "verbatimLatitude verbatimLongitude minimumElevationInMeters "
            "maximumElevationInMeters minimumDepthInMeters maximumDepthInMeters "
            "year month day eventDate dateIdentified identifiedBy recordedBy "
            "individualCount occurrenceStatus identificationVerificationStatus "
            "institutionCode collectionCode catalogNumber datasetID references "
            "continent habitat sex lifeStage establishmentMeans"
        ).split()
    ]
)

METAFILE = """<archive xmlns="http://rs.tdwg.org/dwc/text/">
  <core encoding="UTF-8" fieldsTerminatedBy="\\t" linesTerminatedBy="\\n" \
fieldsEnclosedBy="" ignoreHeaderLines="0" rowType="http://rs.tdwg.org/dwc/terms/Occurrence">
    <files><location>occurrence.txt</location></files>
    <id index="0" />
{fields}
  </core>
</archive>
"""

SAMPLE = [
    "PRESERVED_SPECIMEN", "Chelonodon fluviatilis (Hamilton, 1822)", "Animalia",
    "Chordata", "Actinopterygii", "Tetraodontiformes", "Tetraodontidae", "Tetraodon",
    "India", "Andaman and Nicobar Islands", "Port Blair", "11.6234", "92.7265",
    "1930", "4", "1", "Misra, K. S.; Rao, H. Srinivasa", "CAS", "SU (ICH)",
]


def main(directory, row_count):
    os.makedirs(directory, exist_ok=True)

    fields = "\n".join(
        '    <field index="{i}" term="{t}"/>'.format(i=i, t=term)
        for i, term in enumerate(TERMS)
    )
    with open(os.path.join(directory, "meta.xml"), "w", encoding="utf-8") as f:
        f.write(METAFILE.format(fields=fields))

    column_count = len(TERMS)
    with open(
        os.path.join(directory, "occurrence.txt"), "w", encoding="utf-8", newline=""
    ) as f:
        for i in range(row_count):
            cells = [str(600000000 + i), str(900000000 + i)]
            while len(cells) < column_count:
                cells.append(SAMPLE[len(cells) % len(SAMPLE)])
            f.write("\t".join(cells[:column_count]) + "\n")

    size = os.path.getsize(os.path.join(directory, "occurrence.txt"))
    print(
        "wrote {n} rows, {c} columns, {mb:.0f}MB to {d}".format(
            n=row_count, c=column_count, mb=size / (1024 * 1024), d=directory
        )
    )


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
