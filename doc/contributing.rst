Contributing
============

Contributions are more than welcome !

Running the test suite
----------------------

::
    
    $ pip install nose
    $ nosetests

Test coverage can easily be obtained after installing `coverage.py`_

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

.. _coverage.py: http://nedbatchelder.com/code/coverage/