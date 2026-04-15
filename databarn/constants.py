"""Core constants shared across DataBarn internals."""

from .trails import Sentinel

# Marker used when a value is intentionally missing/unset.
MISSING_ARG = Sentinel("MISSING_ARG")
ABSENT = Sentinel("ABSENT")
# Reserved internal attribute name attached to every Cob/model.
RESERVED_ATTR_NAME = '__dna__'
POST_INIT_ATTR_NAME = "__databarn_post_init__"
