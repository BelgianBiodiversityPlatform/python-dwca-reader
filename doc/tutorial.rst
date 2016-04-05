Tutorial
========

Installation
------------

Quite simply:

::
    
    $ pip install python-dwca-reader

Example uses
------------

Basic use, access to metadata and rows from the Core file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from dwca.read import DwCAReader
    from dwca.darwincore.utils import qualname as qn

    # Let's open our archive...
    # Using the with statement ensure that resources will be properly freed/cleaned after use.
    with DwCAReader('my-archive.zip') as dwca:
        # We can now interact with the 'dwca' object

        # We can read scientific metadata (EML) through a xml.etree.ElementTree.Element object in the 'metadata'
        # attribute.
        dwca.metadata

        # The 'descriptor' attribute gives access to the Archive Descriptor (meta.xml) and allow
        # inspecting the archive:
        # For example, discover what the type the Core file is: (Occurrence, Taxon, ...)
        print "Core type is: %s" % dwca.descriptor.core.type
        # => Core type is: http://rs.tdwg.org/dwc/terms/Occurrence

        # Check if a Darwin Core term in present in the core file
        if 'http://rs.tdwg.org/dwc/terms/locality' in dwca.descriptor.core.terms:
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
        if qn('locality') in dwca.descriptor.core.terms:
            pass

        # Or:
        if dwca.descriptor.core.type == qn('Occurrence'):
            pass

        # Finally, let's iterate over the archive core rows and get the data:
        for row in dwca:
            # row is an instance of CoreRow
            # iteration respects their order of appearance in the core file

            # Print can be used for debugging purposes...
            print row

            # => --
            # => Rowtype: http://rs.tdwg.org/dwc/terms/Occurrence
            # => Source: Core file
            # => Row ID:
            # => Data: {u'http://rs.tdwg.org/dwc/terms/basisOfRecord': u'Observation', u'http://rs.tdwg.org/dwc/terms/family': # => u'Tetraodontidae', u'http://rs.tdwg.org/dwc/terms/locality': u'Borneo', u'http://rs.tdwg.#
            # => org/dwc/terms/scientificName': u'tetraodon fluviatilis'}
            # => --

            # You can get the value of a specific Darwin Core term through
            # the "data" dict:
            print "Value of 'locality' for this row: %s" % row.data[qn('locality')]
            # => Value of 'locality' for this row: Mumbai

        # Alternatively, we can get a list of core rows instead of iterating:
        # BEWARE: all rows will be loaded in memory!
        rows = dwca.rows

        # Or retrieve a specific row by its id:
        occurrence_number_three = dwca.get_row_by_id(3)

        # Caution: ids are generally a fragile way to identify a core row in an archive, since the standard dosn't guarantee unicity (nor even that there will be an id).
        # the index (position) of the row (starting at 0) is generally preferable.

        occurrence_on_second_line = dwca.get_row_by_index(1)

        # We can retreive the (absolute) of embedded files
        # NOTE: this path point to a temporary directory that will be removed at the end of the DwCAReader object life cycle.
        path = dwca.absolute_temporary_path('occurrence.txt')


Access to Darwin Core Archives with extensions (star schema)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from dwca.read import DwCAReader

    with DwCAReader('archive_with_vernacularnames_extension.zip') as dwca:
        # Let's ask the archive what kind of extensions are in use:
        for e in dwca.descriptor.extensions:
            print e.type
        # => http://rs.gbif.org/terms/1.0/VernacularName

        first_core_row = dwca.rows[0]

        # Extension rows are accessible from a core row as a list of ExtensionRow instances:
        for extension_line in first_core_row.extensions:
            # Display all rows from extension files reffering to the first Core row
            print extension_line


Another example with multiple extensions (no new API here)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from dwca.read import DwCAReader

    with DwCAReader('multiext_archive.zip') as dwca:
        rows = dwca.rows
        ostrich = rows[0]

        print "You'll find below all extensions rows reffering to Ostrich"
        print "There should be 3 vernacular names and 2 taxon description"
        for ext in ostrich.extensions:
            print ext

        print "We can then simply filter by type..."
        for ext in ostrich.extensions:
            if ext.rowtype == 'http://rs.gbif.org/terms/1.0/VernacularName':
                print ext

4. GBIF Data Portal exports
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. warning:: This feature will soon be deprecated.

The GBIF Data Portal allow users to export searched occurrences as a zip file. The file format is actually a slightly augmented version of `Darwin Core Archive`_ (see :doc:`gbif_results`) that can also be read with this library in two different ways:

- As a standard DwC-A file (see example above). In this case you won't have access to the additional, non-standard features.
- Via the specific ``GBIFResultsReader``, see example below:


.. code:: python

    from dwca.read import GBIFResultsReader

    with GBIFResultsReader('gbif-results.zip') as results:
        # GBIFResultsReader being a subclass of DwCAReader, all previously described features will work the same.
        #
        # But there's more:
        #
        # 1) GBIF Portal downloads include citation and IP rights information about the resultset. They can be accessed via specific attributes:

        print results.citations
        # => "Please cite this data as follows, and pay attention to the rights documented in the rights.txt: ..."

        print results.rights
        # => "Dataset: [Name and license of source datasets for this resultset]"

        # 2) In addition to the dataset-wide metadata (EML) file, these archives also include the source metadata for all datasets whose rows are part of the resultset.

        # 2.1) At the archive level, they can be accessed as a dict:
        print results.source_metadata
        # {'dataset1_UUID': <dataset1 EML (xml.etree.ElementTree.Element instance)>,
        #  'dataset2_UUID': <dataset2 EML (xml.etree.ElementTree.Element instance)>, ...}

        # 2.2 From a CoreRow instance, we can get back to the metadata of its source dataset:
        first_row = results.get_row_by_index(0)
        
        print first_row.source_metadata
        # => <Source dataset EML (Element instance)>


.. _Darwin Core Archive: http://en.wikipedia.org/wiki/Darwin_Core_Archive