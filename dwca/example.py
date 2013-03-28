# This is a temporary file used to demonstrate and test the API
# It will be replaced by proper test and documentation.

import os

from dwca import DwCAReader
from darwincore import qualname as qn

source_path = os.path.join(os.path.dirname(__file__),
                           './test/sample_files/dwca-simple-test-archive.zip')

# Create the object and open the DwC-A file
# You should use the with statement to have automatic cleanup of
# temporary files
with DwCAReader(source_path) as dwca:

    # You can read scientific metadata (EML) thru a BeautifulStoneSoup object
    print dwca.metadata.prettify()

    # You can get inspect archive to discover what is the core type:
    print "Core type is: %s" % dwca.core_type

    # Check if a Darwin Core term in present in the core file
    if dwca.core_contains_term('http://rs.tdwg.org/dwc/terms/locality'):
        print "This archive contains the 'locality' term in its core file."
    else:
        print "Locality term is not present."

    # Terms should be expressed as full qualnames,
    # such as : http://rs.tdwg.org/dwc/terms/country
    # The qn function can help transform short term to qualname: qn('country')
    if dwca.core_contains_term(qn('country')):
        print "This archive contains the 'country' term in its core file."
    else:
        print "'Country' term is not present."

    # Iterate over each line
    for line in dwca.each_line():
        # line is an instance of DwCALine

        # You can use print for debugging purposes...
        print line

        # You can get the value of a specific Darwin Core term:
        print "Locality for this line is: %s" % line.get(qn('locality'))
