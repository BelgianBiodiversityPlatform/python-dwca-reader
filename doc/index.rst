
Home
====

What is python-dwca-reader?
---------------------------

A simple Python package to read and parse `Darwin Core Archive`_ (DwC-A) files, as produced by the `GBIF website`_, the `IPT`_ and many other biodiversity informatics tools.

It intends to be Pythonic and simple to use.

Archives can be enclosed in either a directory or a zip/tgz archive. 

It supports most common features from the Darwin Core Archive standard, including extensions and `Simple Darwin Core`_ expressed as text (aka Archives consisting of a single CSV data file, possibly with Metadata but without Metafile).

It officially supports Python 2.7, 3.5, 3.6 and has been reported to work on Jython by at least one user. It works on Linux, Mac OS and since v0.10.2 also on Windows.

Status
------

It is currently considered beta quality. It helped many users accross the world, but the API is still slightly moving (for the better!)

Concerning performances, it has been reported to work fine with 50Gb archives.

Major limitations
-----------------

- It doesn't currently fully implement the Darwin Core Archive standard, but focus on the most common/useful features. Don't hesitate to report any incompatible DwC-A on the `GitHub repository`_, and we'll do our best to support it. 
- No write support.


.. toctree::
   :maxdepth: 2
   :hidden:

   self
   tutorial
   api
   gbif_results
   changelog
   contributing
   

Indices and tables
------------------

* :ref:`genindex`
* :ref:`search`

.. _GBIF website: http://www.gbif.org
.. _Darwin Core Archive: http://en.wikipedia.org/wiki/Darwin_Core_Archive
.. _IPT: https://github.com/gbif/ipt
.. _GitHub repository: https://github.com/BelgianBiodiversityPlatform/python-dwca-reader
.. _Simple Darwin Core: http://rs.tdwg.org/dwc/terms/simple/
