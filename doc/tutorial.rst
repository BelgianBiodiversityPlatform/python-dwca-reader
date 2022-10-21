Tutorial
========

Example uses
------------

Basic use, access to metadata and data from the Core file
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
        print("Core type is: %s" % dwca.descriptor.core.type)
        # => Core type is: http://rs.tdwg.org/dwc/terms/Occurrence

        # Check if a Darwin Core term in present in the core file
        if 'http://rs.tdwg.org/dwc/terms/locality' in dwca.descriptor.core.terms:
            print("This archive contains the 'locality' term in its core file.")
        else:
            print("Locality term is not present.")

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

            # Print() can be used for debugging purposes...
            print(row)

            # => --
            # => Rowtype: http://rs.tdwg.org/dwc/terms/Occurrence
            # => Source: Core file
            # => Row ID:
            # => Data: {u'http://rs.tdwg.org/dwc/terms/basisOfRecord': u'Observation', u'http://rs.tdwg.org/dwc/terms/family': # => u'Tetraodontidae', u'http://rs.tdwg.org/dwc/terms/locality': u'Borneo', u'http://rs.tdwg.#
            # => org/dwc/terms/scientificName': u'tetraodon fluviatilis'}
            # => --

            # You can get the value of a specific Darwin Core term through
            # the "data" dict:
            print("Value of 'locality' for this row: %s" % row.data[qn('locality')])
            # => Value of 'locality' for this row: Mumbai

        # Alternatively, we can get a list of core rows instead of iterating:
        # BEWARE: all rows will be loaded in memory!
        rows = dwca.rows

        # Or retrieve a specific row by its id:
        occurrence_number_three = dwca.get_corerow_by_id(3)

        # Caution: ids are generally a fragile way to identify a core row in an archive, since the standard doesn't
        # guarantee unicity (nor even that there will be an id). The index (position) of the row (starting at 0) is
        # generally preferable.

        occurrence_on_second_line = dwca.get_row_by_index(1)

        # We can retreive the (absolute) of embedded files
        # NOTE: this path point to a temporary directory that will be removed at the end of the DwCAReader object life
        # cycle.
        path = dwca.absolute_temporary_path('occurrence.txt')


Access to Darwin Core Archives with extensions (star schema)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from dwca.read import DwCAReader

    with DwCAReader('archive_with_vernacularnames_extension.zip') as dwca:
        # Let's ask the archive what kind of extensions are in use:
        for e in dwca.descriptor.extensions:
            print(e.type)
        # => http://rs.gbif.org/terms/1.0/VernacularName

        first_core_row = dwca.rows[0]

        # Extension rows are accessible from a core row as a list of ExtensionRow instances:
        for extension_line in first_core_row.extensions:
            # Display all rows from extension files reffering to the first Core row
            print(extension_line)


Another example with multiple extensions (no new API here)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code:: python

    from dwca.read import DwCAReader

    with DwCAReader('multiext_archive.zip') as dwca:
        rows = dwca.rows
        ostrich = rows[0]

        print("You'll find below all extensions rows reffering to Ostrich")
        print("There should be 3 vernacular names and 2 taxon description")
        for ext in ostrich.extensions:
            print(ext)

        print("We can then simply filter by type...")
        for ext in ostrich.extensions:
            if ext.rowtype == 'http://rs.gbif.org/terms/1.0/VernacularName':
                print(ext)


GBIF Downloads
~~~~~~~~~~~~~~

The GBIF website allow visitors to export occurrences as a Darwin Core Archive. The resulting file contains a few more
things that are not part of the `Darwin Core Archive`_ standard. These additions also works with python-dwca-reader.
See :doc:`gbif_results` for explanations on the file format and how to use it.

.. _Darwin Core Archive: http://en.wikipedia.org/wiki/Darwin_Core_Archive

Data analysis and manipulation with Pandas
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Python-dwca-reader provides specific tools to make working with Pandas easier, see :doc:`pandas_tutorial` for concrete
examples.
