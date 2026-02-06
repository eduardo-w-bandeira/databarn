from .trails import Sentinel

ABSENT = Sentinel("ABSENT")
NO_VALUE = Sentinel("NO_VALUE")
RESERVED_ATTR_NAME = '__dna__'
SPECIAL_ATTR_NAMES = (RESERVED_ATTR_NAME, '__post_init__')
