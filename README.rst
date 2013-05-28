What is it ?
============

A simple Python class to read `Darwin Core Archive`_ (DwC-A) files.

Status
======

It is currently considered alpha quality. It helped its author a couple of times, but should be improved and tested before widespread use.

Major limitations
-----------------

- Early support for DwC-A extensions.
- It sometimes assumes the file has been produced by GBIF's IPT_. For example, only zip compression is curently supported, even tough the Darwin Core Archive allows other compression formats.
- No write support.

Tutorial
========

Installation
------------

Quite simply:

::
    
    $ pip install python-dwca-reader

Example use
-----------

1. Basic use, access to metadata and "Core lines"

.. code:: python

    from dwca import DwCAReader
    from darwincore.utils import qualname as qn

    # Let's open our archive...
    # Using the with statement ensure that resources will be properly freed/cleaned after use.
    with DwCAReader('my_archive.zip') as dwca:
        # We can now interact with the 'dwca' object

        # We can read scientific metadata (EML) through a BeautifulStoneSoup object in the 'metadata' attribute
        # BeautifulStoneSoup is provided by BS3: http://www.crummy.com/software/BeautifulSoup/bs3/documentation.html
        print dwca.metadata.prettify()

        # We can get inspect archive to discover what is the Core Type (Occurrence, Taxon, ...):
        print "Core type is: %s" % dwca.core_rowtype
        # => Core type is: http://rs.tdwg.org/dwc/terms/Occurrence

        # Check if a Darwin Core term in present in the core file
        if dwca.core_contains_term('http://rs.tdwg.org/dwc/terms/locality'):
            print "This archive contains the 'locality' term in its core file."
        else:
            print "Locality term is not present."

        # Using full qualnames for DarwincCore terms (such as 'http://rs.tdwg.org/dwc/terms/country') is verbose...
        # The qualname() helper function make life easy for common terms.
        # (here, it has been imported as 'qn'):
        qn('locality')
        # => u'http://rs.tdwg.org/dwc/terms/locality'

        # Combined with previous examples, this can be used to things more clear:
        # For example:
        if dwca.core_contains_term(qn('locality')):
            pass

        # Or:
        if dwca.core_rowtype == qn('Occurrence'):
            pass

        # Finally, let's iterate over the archive lines and get the data:
        for line in dwca.each_line():
            # line is an instance of DwCALine

            # Print can be used for debugging purposes...
            print line

            # => --
            # => Rowtype: http://rs.tdwg.org/dwc/terms/Occurrence
            # => Source: Core file
            # => Line ID:
            # => Data: {u'http://rs.tdwg.org/dwc/terms/basisOfRecord': u'Observation', u'http://rs.tdwg.org/dwc/terms/family': # => u'Tetraodontidae', u'http://rs.tdwg.org/dwc/terms/locality': u'Borneo', u'http://rs.tdwg.# 
            # => org/dwc/terms/scientificName': u'tetraodon fluviatilis'}
            # => --

            # You can get the value of a specific Darwin Core term through
            # the "data" dict:
            print "Locality for this line is: %s" % line.data[qn('locality')]
            # => Locality for this line is: Mumbai

        # Alternatively, we can get a list of core lines instead of using each_line():
        lines = dwca.lines

        # Or retrieve a specific line by its id:
        occurrence_number_three = dwca.get_line(3)

2. Use of Darwin Core Archives using extensions (star schema)

.. code:: python

    from dwca import DwCAReader
    from darwincore.utils import qualname as qn

    with DwCAReader('archive_with_vernacularnames_extension.zip') as dwca:
        # Let's ask the archive what kind of extensions are in use:
        print dwca.extensions_rowtype
        # => [u'http://rs.gbif.org/terms/1.0/VernacularName']

        # For convenience
        core_lines = dwca.lines

        # a) Data access
        # Extension lines are accessible as a list of DwcALine instances in the 'extensions' attribute:
        for e in core_lines[0].extensions:
            # Display all extensions line that refers to the first Core line
            print e

        # b) We can now see in a given archive, a DwcALine can come from multiple sources...
        # Se we can ask it where it's from:
        print core_lines[0].from_core
        # => True
        print core_lines[0].extensions[0].from_extension
        # => True

        # ... and what its rowtype is:
        print core_lines[0].rowtype
        # => http://rs.tdwg.org/dwc/terms/Taxon

3. Another example with multiple extensions (no new API here):

.. code:: python

    from dwca import DwCAReader
    from darwincore.utils import qualname as qn

    with DwCAReader('multiext_archive.zip') as dwca:
        lines = dwca.lines
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


Run the test suite
------------------

::
    
    $ pip install nose
    $ nosetests

Test coverage can easily be obtained after installing `coverage.py`_

::

    $ nosetests --with-coverage --cover-erase --cover-package=dwca
    .....................
    Name                    Stmts   Miss  Cover   Missing
    -----------------------------------------------------
    dwca                        0      0   100%
    dwca.darwincore             0      0   100%
    dwca.darwincore.terms       1      0   100%
    dwca.darwincore.utils       3      0   100%
    dwca.dwca                 130     16    88%   23-45
    dwca.utils                  5      1    80%   12
    -----------------------------------------------------
    TOTAL                     139     17    88%
    ----------------------------------------------------------------------
    Ran 21 tests in 0.830s

    OK


.. _Darwin Core Archive: http://en.wikipedia.org/wiki/Darwin_Core_Archive
.. _IPT: https://code.google.com/p/gbif-providertoolkit/
.. _coverage.py: http://nedbatchelder.com/code/coverage/
