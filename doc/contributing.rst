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
    ..................................
    Name                    Stmts   Miss  Cover   Missing
    -----------------------------------------------------
    dwca                        1      0   100%
    dwca.darwincore             0      0   100%
    dwca.darwincore.terms       1      0   100%
    dwca.darwincore.utils       3      0   100%
    dwca.dwca                  84      0   100%
    dwca.lines                 67      4    94%   112, 115, 138, 141
    dwca.utils                 38      9    76%   36-49
    -----------------------------------------------------
    TOTAL                     194     13    93%
    ----------------------------------------------------------------------
    Ran 34 tests in 3.515s

    OK

Building the doc
----------------

Locally:

::

    $ cd doc; make clean; make html

Online (http://python-dwca-reader.readthedocs.org/):

The docs will be updated automagically upon commit on GitHub thanks to Webhooks.


Releasing
---------

* (Ensuring it works, the test coverage is good and the documentation is updated)
* Update the packaging (version number in setup.py, CHANGES.txt) then run
    
::

    $ python setup.py sdist upload

* Also update the version in doc/conf.py
* Create a new tag and push it to GitHub

::

    $ git tag vX.Y.Z
    $ git push origin --tags

.. _coverage.py: http://nedbatchelder.com/code/coverage/