class Unset:
    """A unique sentinel object to detect not-set values."""

    def __repr__(self):
        return f"<{self.__class__.__name__}>"

UNSET = Unset()

PROTECTED_ATTR_NAME = '__dna__'