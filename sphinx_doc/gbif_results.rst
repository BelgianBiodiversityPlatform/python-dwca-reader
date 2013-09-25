Description of the GBIF Data Portal Occurrence download format
==============================================================

As of late 2013, the new version [1]_ of the GBIF Data Portal now exports occurrences (search results) in a format that is a superset on the Darwin Core Archive standard.

Python-dwca-reader provides a specialized ``GBIFResultsReader`` class that gives access to its specificities. The rest of this document describe the file format.

Additions to the Darwin Core Archive standard & specificities:
--------------------------------------------------------------

* In addition to the general metadata file (``metadata.xml``), it contains a ``dataset`` directory. Each file in this directory is an EML document describing a dataset whose occurences are part of the search results. The file name (without extension) is the UUID of this dataset. Each line in occurrence.txt refers to this file using the ``datasetID`` Darwin Core term. These UUID's can also be resolved using the `GBRDS Registry`_.
* It contains rights.txt and citations.txt that provides aggregated IP rights and citation information for these search results. These two files are not referenced in the archive descriptor (``meta.xml``)

Examples:
---------

If a row in ``occurrence.txt`` has the '4bfac3ea-8763-4f4b-a71a-76a6f5f243d3' value in its ``datasetID`` column, we can find an EML file corresponding to the originating dataseet in the ``dataset/4bfac3ea-8763-4f4b-a71a-76a6f5f243d3.xml`` file. This dataset can also be found in the GBIF Registry at: http://gbrds.gbif.org/browse/agent?uuid=4bfac3ea-8763-4f4b-a71a-76a6f5f243d3 .

A consumer of these search results can use the content of citations.txt and rights.txt to check use is allowed and properly cite the data originator.

sample citations.txt:

::

    Please cite this data as follows, and pay attention to the rights documented in the rights.txt: 
    Please respect the rights declared for each dataset in the download: 
    Yale Peabody Museum, (c) 2009. Specimen data records available through distributed digital resources.
    Senckenberg: Collection Pisces SMF
    Field Museum: Field Museum of Natural History (Zoology) Fish Collection
    Zoological Museum, Natural History Museum of Denmark: The Fish Collection
    Gothenburg Natural History Museum (GNM): Vertebrates of the Gothenburg Natural History Museum (GNM)
    Swedish Museum of Natural History: NRM-Fishes
    BeBIF Provider: University of Ghent - Zoology Museum - Vertebratacollectie


sample rights.txt:

::

    Dataset: Peabody Ichthyology DiGIR Service
    Rights as supplied: Peabody Museum data records may be used by individual researchers or research groups, but they may not be repackaged, resold, or redistributed in any form without the express written consent of a curatorial staff member of the museum. If any of these records are used in an analysis or report, the provenance of the original data must be acknowledged and the Peabody notified. Yale University and the Peabody Museum of Natural History and its staff are not responsible for damages, injury or loss due to the use of these data.

    Dataset: Collection Pisces SMF
    Rights as supplied: Not supplied

    Dataset: Field Museum of Natural History (Zoology) Fish Collection
    Rights as supplied: Copyright © 2012 The Field Museum of Natural History
    Full details may be found at http://fieldmuseum.org/about/copyright-information

    Dataset: The Fish Collection
    Rights as supplied: GBIF Data Sharing Agreement is applied.  GBIF Data Use Agreement is applied.

    Dataset: Vertebrates of the Gothenburg Natural History Museum (GNM)
    Rights as supplied: Not supplied

    Dataset: NRM-Fishes
    Rights as supplied: Not supplied

    Dataset: University of Ghent - Zoology Museum - Vertebratacollectie
    Rights as supplied: Not supplied

.. _GBRDS Registry: http://gbrds.gbif.org/index
.. [1] currently in development/beta at http://uat.gbif.org