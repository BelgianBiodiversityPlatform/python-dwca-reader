Contributing
============

Contributions are more than welcome! Please also provide tests and documentation for your contributions.

Running the test suite
----------------------

::
    
    $ pip install nose
    $ nosetests

Test coverage can be obtained after installing `coverage.py`_

::

    nosetests --with-coverage --cover-erase --cover-package=dwca
    ..........................................................................
    Name                       Stmts   Miss  Cover
    ----------------------------------------------
    dwca.py                        0      0   100%
    dwca/darwincore.py             0      0   100%
    dwca/darwincore/terms.py       1      0   100%
    dwca/darwincore/utils.py       4      0   100%
    dwca/descriptors.py           90      1    99%
    dwca/exceptions.py             4      0   100%
    dwca/files.py                 60      0   100%
    dwca/read.py                 141      1    99%
    dwca/rows.py                  78      4    95%
    ----------------------------------------------
    TOTAL                        378      6    98%
    ----------------------------------------------------------------------
    Ran 74 tests in 1.119s

    OK

Building the documentation
--------------------------

Locally:

::

    $ pip install sphinx sphinx-rtd-theme
    $ cd doc; make clean; make html

Online at http://python-dwca-reader.readthedocs.org/:

The online docs will be updated automagically after pushing to GitHub.


Releasing at PyPI
-----------------

* (Ensuring it works, the test coverage is good and the documentation is updated)
* Update the packaging (version number in setup.py, CHANGES.txt, doc/conf.py, ...) then run:
    
::

    $ python setup.py sdist upload

* Create a new tag and push it to GitHub

::

    $ git tag vX.Y.Z
    $ git push origin --tags

.. _coverage.py: http://nedbatchelder.com/code/coverage/