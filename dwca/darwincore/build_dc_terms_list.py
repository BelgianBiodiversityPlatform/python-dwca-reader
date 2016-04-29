# -*- coding: utf-8 -*-
"""Utility script to generate a list of DarwinCore terms (to be consumed by qualname())."""

# Utility script used during development to generate a list of DarwinCore
# terms from Darwin Core description XML files. This list of terms is for
# consumption by the qualname() helper

# Usage example:
# python build_dc_terms_list.py source_data/dwc_occurrence.xml \
#                               source_data/dwc_taxon.xml > terms.py

import argparse
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description="Generate a list of qualnames "
                                             "of Darwin Core terms from XML "
                                             "description files.")

# Required positional argument: one or more XML files to be read
parser.add_argument('source_xml', nargs='+', type=argparse.FileType('r'))
parser.parse_args()
args = parser.parse_args()

# Use a set to remove possible duplicates
qualnames = set()

for source_file in args.source_xml:
    root = ET.parse(source_file).getroot()
    # First, extract the RowType itself... (Occcurrence, Taxon, ...)
    qualnames.add(root.get('rowType'))

    # Store each qualname found in any tag to our set
    for ch in root.iter():
        qn = ch.get('qualName')
        if qn:
            qualnames.add(qn)

# Turn set to list and add the variable name in front so output can directly be
# redirected in a file (quick'n'dirty)
print("TERMS = " + repr(list(qualnames)))
