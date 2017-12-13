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
    Name                          Stmts   Miss  Cover
    -------------------------------------------------
    dwca/__init__.py                  0      0   100%
    dwca/darwincore/__init__.py       0      0   100%
    dwca/darwincore/terms.py          1      0   100%
    dwca/darwincore/utils.py          4      0   100%
    dwca/descriptors.py              92      1    99%
    dwca/exceptions.py                5      0   100%
    dwca/files.py                    63      1    98%
    dwca/read.py                    186      1    99%
    dwca/rows.py                     96     11    89%
    dwca/vendor.py                    5      2    60%
    -------------------------------------------------
    TOTAL                           452     16    96%
    ----------------------------------------------------------------------
    Ran 104 tests in 1.514s

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

* (Ensuring it works -also on Windows-, the test coverage is good and the documentation is updated)
* Update the packaging (version number in setup.py, CHANGES.txt, doc/conf.py, ...) then run:
    
::

    $ python setup.py sdist upload

* Create a new tag and push it to GitHub

::

    $ git tag vX.Y.Z
    $ git push origin --tags

.. _coverage.py: http://nedbatchelder.com/code/coverage/