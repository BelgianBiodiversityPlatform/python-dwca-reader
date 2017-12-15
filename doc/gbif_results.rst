The GBIF Occurrence download format
===================================

Since 2013, the `GBIF Data Portal`_ exports occurrences (search results) in a format that is a superset of the Darwin Core Archive standard.

Python-dwca-reader used to provide a specialized ``GBIFResultsReader`` class that gave access to its specificities. ``GBIFResultsReader`` is now deprecated, but its features have been merged into ``DwCAReader``. The rest of this document describe the specifics of GBIF downloads, and how to use them with python-dwca-reader.

Additions to the Darwin Core Archive standard & how to use
----------------------------------------------------------

.. warning:: Those additions are not part of the official standard, and the GBIF download format can evolve at any point without prior announcement.

Source metadata
~~~~~~~~~~~~~~~

In addition to the general metadata file (``metadata.xml``), the archive also contains a ``dataset`` subdirectory. Each file in this subdirectory is an EML document describing a dataset whose rows are part of the archive data. The file name is ``"<DATASET_UUID>.xml"``. Each row in ``occurrence.txt`` refers to this file using the ``datasetID`` column. 

You can access this source metadata like this:

.. code:: python

    from dwca.read import DwCAReader

    with DwCAReader('gbif-results.zip') as results:
        # 1. At the archive level, through the source_metadata dict:
        
        print(results.source_metadata)
        # {'dataset1_UUID': <dataset1 EML (xml.etree.ElementTree.Element instance)>,
        #  'dataset2_UUID': <dataset2 EML (xml.etree.ElementTree.Element instance)>, ...}

        # 2. From a CoreRow instance, we can get back to the metadata of its source dataset:
        first_row = results.get_row_by_index(0)
        print(first_row.source_metadata)
        # => <Source dataset EML (xml.etree.ElementTree.Element instance)>

Interpreted/verbatim occurrences and multimedia data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

While the Core data file (``occurrence.txt``) contains GBIF-interpreted occurrences, the verbatim (as published) data is also made available with an extension in ``verbatim.txt``. Similarly, if there's multimedia information attached to the record it will be availabe in the ``multimedia.txt`` extension file.

Because there's a standard core-extension relationship (star schema) between those entities, you can access the related data from the core row using the usual extension mechanism:

.. code:: python

    from dwca.read import DwCAReader

    with DwCAReader('gbif-results.zip') as results:
        first_row = results.get_row_by_index(0)

        first_row.extensions

Additional text files
~~~~~~~~~~~~~~~~~~~~~

The archive contains additional files such as ``rights.txt`` (aggregated IP rights) and ``citations.txt`` (citation information for the search results).

You can access the content of those files: 

.. code:: python

    from dwca.read import DwCAReader

    with DwCAReader('gbif-results.zip') as results:
        citations = results.open_included_file('citations.txt').read()

.. _GBIF Data Portal: http://www.gbif.org/occurrence