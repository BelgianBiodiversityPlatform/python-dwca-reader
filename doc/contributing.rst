Contributing
============

Contributions are more than welcome !

Running the test suite
----------------------

::
    
    $ pip install nose
    $ nosetests

Test coverage can be obtained after installing `coverage.py`_

::

    $ nosetests --with-coverage --cover-erase --cover-package=dwca
    .....................................
    Name                    Stmts   Miss  Cover   Missing
    -----------------------------------------------------
    dwca                        1      0   100%
    dwca.darwincore             0      0   100%
    dwca.darwincore.terms       1      0   100%
    dwca.darwincore.utils       3      0   100%
    dwca.dwca                  91      0   100%
    dwca.rows                  65      4    94%   143, 146, 181, 184
    dwca.utils                 45      9    80%   28-41
    -----------------------------------------------------
    TOTAL                     206     13    94%
    ----------------------------------------------------------------------
    Ran 37 tests in 3.995s

    OK

Building the documentation
--------------------------

Locally:

::

    $ cd doc; make clean; make html

Online at http://python-dwca-reader.readthedocs.org/:

The docs will be updated automagically upon commit on GitHub thanks to Webhooks.


Releasing at PyPI
-----------------

* (Ensuring it works, the test coverage is good and the documentation is updated)
* Update the packaging (version number in setup.py, CHANGES.txt) then run:
    
::

    $ python setup.py sdist upload

* Also update the version in doc/conf.py
* Create a new tag and push it to GitHub

::

    $ git tag vX.Y.Z
    $ git push origin --tags

.. _coverage.py: http://nedbatchelder.com/code/coverage/