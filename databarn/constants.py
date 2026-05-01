"""Core constants shared across DataBarn internals."""

from .trails import Sentinel

MISSING_ARG = Sentinel("MISSING_ARG")  # Sentinel for missing arg.
ABSENT = Sentinel("ABSENT")  # Sentinel for absent value (unset or deleted).
# Reserved internal attribute name attached to every Cob/model.
RESERVED_SYMBOL = '__dna__'
POST_INIT_SYMBOL = "__databarn_post_init__"
BEFORE_ASSIGN_SYMBOL = "__databarn_before_assign__"
POST_ASSIGN_SYMBOL = "__databarn_post_assign__"
