Contributing to Python-dwca-reader
==================================

Contributions are more than welcome! Please also provide tests and documentation for your contributions.

Running the test suite
----------------------

::
    
    $ pip install -r requirements-dev.txt
    $ pytest

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
* Update the packaging (version number in dwca/version.py, CHANGES.txt, ...) then run:
    
::

    $ python setup.py sdist bdist_wheel
    $ twine upload dist/*

* Create a new tag and push it to GitHub

::

    $ git tag vX.Y.Z
    $ git push origin --tags

.. _coverage.py: http://nedbatchelder.com/code/coverage/