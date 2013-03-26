What is it ?
============

A simple Python class to read `Darwin Core Archive`_ (DwC-A) files.

Status
======

It is currently considered pre-alpha quality. It helped its author a couple of times, but should be improved and tested before widespread use.

Major limitations
-----------------

- If the archive contains Darwin Core Extensions, it's (currently) not able to access this data. Only (EML) metadata and Core data file are readable. This limitation should be removed soon.
- It sometimes assumes the file has been produced by GBIF's IPT_. For example, only zip compression is curently supported, even tough the Darwin Core Archive allows other compression formats.
- No write support.
- Need a solid test suite.

Tiny tutorial
=============

Installation
------------

A proper Python package will be provided as soon as the code is considered beta quality.

In the meantime, just copy it to your PYTHONPATH. It also requires BeautifulSoup (v3), so

::
    
    $ pip install BeautifulSoup

Use
---

A basic example is provided in dwca/example.py.    

.. _Darwin Core Archive: http://en.wikipedia.org/wiki/Darwin_Core_Archive
.. _IPT: https://code.google.com/p/gbif-providertoolkit/

Run the test suite
------------------

::
    
    $ pip install nose
    $ nosetests
