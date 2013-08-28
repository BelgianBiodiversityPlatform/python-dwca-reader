What is it ?
============

A simple Python class to read `Darwin Core Archive`_ (DwC-A) files. It can also read exports (Occurrences downloads) from the new GBIF Data Portal (to be released later in 2013).

Status
======

It is currently considered alpha quality. It helped its author a couple of times, but should be improved and tested before widespread use.

Major limitations
-----------------

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
    from dwca.darwincore.utils import qualname as qn

    # Let's open our archive...
    # Using the with statement ensure that resources will be properly freed/cleaned after use.
    with DwCAReader('my_archive.zip') as dwca:
        # We can now interact with the 'dwca' object

        # We can read scientific metadata (EML) through a BeautifulSoup object in the 'metadata' attribute
        # See BeautifulSoup 4 documentation: http://www.crummy.com/software/BeautifulSoup/bs4/doc
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

        # We can retreive the (absolute) of embedded files
        # NOTE: this path point to a temporary directory that will be removed at the end of the DwCAReader object life cycle.
        path = dwca.absolute_temporary_path('occurrence.txt')


2. Use of Darwin Core Archives using extensions (star schema)

.. code:: python

    from dwca import DwCAReader
    from dwca.darwincore.utils import qualname as qn

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
    from dwca.darwincore.utils import qualname as qn

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

4. GBIF Data Portal exports

The new version of the GBIF Data Portal (to be released later this year) will allow users to export searched occurrences as a zip file. The file format is actually a slightly augmented version of `Darwin Core Archive`_ that can also be read with this library in two different ways:

- As a standard DwC-A file (see example above). In this case you won't have access to the additional, non-standard data.
- Via the specific ``GBIFResultsReader``, see example below:

.. code:: python

    from dwca import GBIFResultsReader

    with GBIFResultsReader('results.zip') as results:
        # GBIFResultsReader being a subclass of DwCAReader, all previously described features will work the same.
        #
        # But there's more:
        #
        # 1) GBIF Portal downloads include citation and IP rights information about the resultset. They can be accessed via specific attributes:

        results.citations
        # => "Please cite this data as follows, and pay attention to the rights documented in the rights.txt: ..."

        results.rights
        # => "Dataset: [Name and license of source datasets for this resultset]"

        # 2) In addition to the dataset-wide metadata (EML) file, these archives also include the source metadata for all datasets whose lines are part of the resultset.

        # 2.1) At the archive level, they can be accessed as a dict:
        results.source_metadata
        # {'dataset1_UUID': <dataset1 EML (BeautifulSoup instance)>,
        #  'dataset2_UUID': <dataset2 EML (BeautifulSoup instance)>, ...}

        # 2.2 From a DwCALine instance, we can get back to the metadata of its source dataset:
        first_line = results.line[0]
        first_line.source_metadata
        => <Source dataset EML (BeautifulSoup instance)>


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
