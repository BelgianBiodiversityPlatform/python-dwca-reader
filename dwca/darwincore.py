def qualname(short):
    """Takes a darwin core term and returns the corresponding qualname

    Ex.: 'Occurrence' will return http://rs.tdwg.org/dwc/terms/Occurrence
    raise a StopIteration if none is found.
    """

    # TODO: Moved outside so not redefined on each call ?
    terms = [
        'http://rs.tdwg.org/dwc/terms/country',
        'http://rs.tdwg.org/dwc/terms/decimalLatitude',
        'http://rs.tdwg.org/dwc/terms/decimalLongitude',
        'http://rs.tdwg.org/dwc/terms/kingdom',
        'http://rs.tdwg.org/dwc/terms/locality',
        'http://rs.tdwg.org/dwc/terms/Occurrence'
    ]

    return next(t for t in terms if t.endswith('/' + short))
