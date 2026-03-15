from .trails import Sentinel

ABSENT = Sentinel("ABSENT")
RESERVED_ATTR_NAME = '__dna__'
SPECIAL_ATTR_NAMES = (RESERVED_ATTR_NAME, '__post_init__')
