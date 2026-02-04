class Absent:
    """A unique sentinel object to indicate no provided argument."""

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


class NoValue:
    """A unique sentinel object to indicate no assigned value to an attribute."""

    def __repr__(self):
        return f"<{self.__class__.__name__}>"


ABSENT = Absent()
NO_VALUE = NoValue()
RESERVED_ATTR_NAME = '__dna__'
SPECIAL_ATTR_NAMES = (RESERVED_ATTR_NAME, '__post_init__')
