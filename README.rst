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

Run the test suite
------------------

::
    
    $ pip install nose
    $ nosetests

Test coverage can easily be obtained after installing `coverage.py`_

::

    $ nosetests --with-coverage --cover-erase --cover-package=dwca
    ....................
    Name              Stmts   Miss  Cover   Missing
    -----------------------------------------------
    dwca                  0      0   100%
    dwca.darwincore       3      0   100%
    dwca.dwca           130     17    87%   23-45, 151
    dwca.utils            5      1    80%   12
    -----------------------------------------------
    TOTAL               138     18    87%
    ----------------------------------------------------------------------
    Ran 20 tests in 0.669s

    OK


.. _Darwin Core Archive: http://en.wikipedia.org/wiki/Darwin_Core_Archive
.. _IPT: https://code.google.com/p/gbif-providertoolkit/
.. _coverage.py: http://nedbatchelder.com/code/coverage/
