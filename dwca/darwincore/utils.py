from .terms import TERMS

def qualname(short):
    """Takes a darwin core term and returns the corresponding qualname

    Ex.: 'Occurrence' will return http://rs.tdwg.org/dwc/terms/Occurrence
    raise a StopIteration if none is found.
    """

    return next(t for t in TERMS if t.endswith('/' + short))
