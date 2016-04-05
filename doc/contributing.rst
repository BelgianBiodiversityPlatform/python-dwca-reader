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

    $ nosetests --with-coverage --cover-erase --cover-package=dwca

    Name                       Stmts   Miss  Cover   Missing
    --------------------------------------------------------
    dwca.py                        0      0   100%
    dwca/darwincore.py             0      0   100%
    dwca/darwincore/terms.py       1      0   100%
    dwca/darwincore/utils.py       4      0   100%
    dwca/descriptors.py           92      1    99%   226
    dwca/exceptions.py             4      0   100%
    dwca/read.py                 142      1    99%   198
    dwca/rows.py                  72      4    94%   161, 164, 193, 196
    dwca/utils.py                 59      0   100%
    --------------------------------------------------------
    TOTAL                        374      6    98%
    ----------------------------------------------------------------------
    Ran 71 tests in 1.608s
    
    OK

Building the documentation
--------------------------

Locally:

::

    $ cd doc; make clean; make html

Online at http://python-dwca-reader.readthedocs.org/:

The docs will be updated automagically upon commit on GitHub (thanks to Webhooks).


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