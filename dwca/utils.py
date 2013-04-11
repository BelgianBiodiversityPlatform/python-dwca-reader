# Mixin class to immplement easy object comparison
# Instances will be considered equals if they are instances
# of the same classes with equal attributes.

class CommonEqualityMixin(object):

    def __eq__(self, other):
        return (isinstance(other, self.__class__)
            and self.__dict__ == other.__dict__)

    def __ne__(self, other):
        return not self.__eq__(other)