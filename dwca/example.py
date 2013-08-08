# This is a temporary file used to demonstrate and test the API
# It will be replaced by proper tests and documentation.

# TODO: Remove very soon, once test and tutorial have been a little more
# confronted to reality.

import os

from dwca import DwCAReader
from darwincore.utils import qualname as qn

source_path = os.path.join(os.path.dirname(__file__),
                           './test/sample_files/dwca-simple-test-archive.zip')

star_path = os.path.join(os.path.dirname(__file__),
                         './test/sample_files/dwca-star-test-archive.zip')

multiext_path = os.path.join(os.path.dirname(__file__),
                             './test/sample_files/dwca-2extensions.zip')

# Create the object and open the DwC-A file
# You should use the with statement to have automatic cleanup of
# temporary files
with DwCAReader(source_path) as dwca:

    # You can read scientific metadata (EML) thru a BeautifulSoup object
    print dwca.metadata.prettify()

    # You can get inspect archive to discover what is the core type:
    print "Core type is: %s" % dwca.core_rowtype

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

        # You can get the value of a specific Darwin Core term through
        # the "data" dict:
        print "Locality for this line is: %s" % line.data[qn('locality')]

star_path = os.path.join(os.path.dirname(__file__),
                         './test/sample_files/dwca-star-test-archive.zip')

print "Now, let's show an Archive that use an extension (VernacularNames)"
with DwCAReader(star_path) as dwca:

    # Let's ask the archive what kind of extensions are in use:
    print "Extensions in use: %s" % dwca.extensions_rowtype

    # We can easily get a list of core lines instead of iterating manually:
    lines = dwca.lines
    print lines[0]

    print "Extension lines are accessible through 'extensions' (list):"
    for e in lines[0].extensions:
        print e

    print "We can ask a DwcALine where it's coming from: "
    print lines[0].from_core
    print lines[0].extensions[0].from_extension

    print "... and what its rowtype is:"
    print lines[0].rowtype

# And now, an archive with multiple extensions
with DwCAReader(multiext_path) as dwca:
    lines = list(dwca.each_line())
    ostrich = lines[0]

    print "You'll find below all extensions line reffering to Ostrich"
    print "There should be 3 verncaular names and 2 taxon description"
    for ext in ostrich.extensions:
        print ext

    print "We can then simply filter by type..."
    for ext in ostrich.extensions:
        if ext.rowtype == 'http://rs.gbif.org/terms/1.0/VernacularName':
            print ext

    print "We can also use list comprehensions for this:"
    description_ext = [e for e in ostrich.extensions if
                       e.rowtype == 'http://rs.gbif.org/terms/1.0/Description']
    for ext in description_ext:
        print ext

    print "We can retrieve a specific line by its id:"
    peliperdix = dwca.get_line(3)
    print peliperdix.__dict__
