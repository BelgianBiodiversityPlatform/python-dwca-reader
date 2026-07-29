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

* Check the GitHub Actions run is green (it covers Linux, macOS and Windows) and that the
  documentation is up to date.
* Update ``dwca/version.py`` and ``CHANGES.txt``, and get that merged to ``main``.
* From a clean checkout of ``main``::

    $ pip install --upgrade build twine
    $ rm -rf build dist
    $ python -m build
    $ twine upload dist/python_dwca_reader-X.Y.Z*

* Tag the released commit and push the tag::

    $ git tag vX.Y.Z
    $ git push origin vX.Y.Z

Four things that have caught us out, all of them worth the extra keystrokes:

* Build with ``python -m build``, not ``python setup.py sdist bdist_wheel``. The latter uses
  whichever setuptools happens to be first on your PATH, and anything older than 69.3 names
  the sdist ``python-dwca-reader-X.Y.Z.tar.gz``, which PyPI rejects outright.
* Delete ``build/`` first. It shadows the ``build`` module, so ``python -m build`` fails with
  a confusing "No module named build".
* Upload only the files for the version being released. ``twine upload dist/*`` also tries to
  re-upload previous releases, and the whole command fails on the first one that already
  exists. ``twine upload --skip-existing dist/*`` is the alternative: it skips whatever is
  already on PyPI.
* Read the Docs builds ``stable`` from the most recent tag, so a documentation fix only shows
  up there once a release contains it.

.. _coverage.py: http://nedbatchelder.com/code/coverage/