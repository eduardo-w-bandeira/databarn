class Unset:
    """A unique sentinel object to detect not-set values."""

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

UNSET = Unset()

RESERVED_ATTR_NAME = '__dna__'

SPECIAL_ATTR_NAMES = (RESERVED_ATTR_NAME, '__post_init__')