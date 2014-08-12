# -*- coding: utf-8 -*-

"""This module contains small helpers to make life easier.

"""

from .terms import TERMS


def qualname(short_term):
    """Takes a darwin core term (short form) and returns the corresponding qualname.

    .. note::

        It is generally used to make data access less verbose (see example below).


    :raises: :class:`StopIteration` if short_term is not found.

    Typical real-world example::

        from dwca.darwincore.utils import qualname as qn

        qn("Occurrence")  # => "http://rs.tdwg.org/dwc/terms/Occurrence"

        # To access data row:
        myrow.data[qn('scientificName')]  # => u"Tetraodon fluviatilis"

        # Instead of the verbose:
        myrow.data['http://rs.tdwg.org/dwc/terms/scientificName']  # => u"Tetraodon fluviatilis"

    """

    return next(t for t in TERMS if t.endswith('/' + short_term))
