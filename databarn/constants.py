"""Core constants shared across DataBarn internals."""

from .trails import Sentinel

# Marker used when a value is intentionally missing/unset.
ABSENT = Sentinel("ABSENT")
# Reserved internal attribute name attached to every Cob/model.
RESERVED_ATTR_NAME = '__dna__'
# Attribute names treated as special by model-building logic.
SPECIAL_ATTR_NAMES = (RESERVED_ATTR_NAME, '__post_init__')
