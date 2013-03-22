# This is a temporary file used to demonstrate and test the API
# It will be replaced by proper test and documentation.

import os

from dwca import DwCAReader
from dwterms import terms

source_path = os.path.join(os.path.dirname(__file__),
                           './test/sample_files/dwca-simple-test-archive.zip')

# Create the object and open the DwC-A file
dwca = DwCAReader(source_path)

# Check if a Darwin Core term in present in the core file
if dwca.core_contains_term('http://rs.tdwg.org/dwc/terms/locality'):
    print "This archive contains the 'locality' term in its core file."
else:
    print "Locality term is not present."

# Shortcuts for Darwin Core terms are available:
# We can use terms['COUNTRY'] instead of the full URL
if dwca.core_contains_term(terms['COUNTRY']):
    print "This archive contains the 'country' term in its core file."
else:
    print "'Country' term is not present."

# Iterate over each line
for line in dwca.each_line():
    # line is an instance of DwCALine
    print line
