"""Core constants shared across DataBarn internals."""

from .trails import Sentinel

MISSING_ARG = Sentinel("MISSING_ARG")  # Sentinel for missing arg.
ABSENT = Sentinel("ABSENT")  # Sentinel for absent value (unset or deleted).
# Reserved internal attribute name attached to every Cob/model.
DNA_SYMBOL = '__dna__'
POST_INIT_SYMBOL = "__databarn_post_init__"
TREAT_BEFORE_ASSIGN_SYMBOL = "__databarn_treat_before_assign__"
POST_ASSIGN_SYMBOL = "__databarn_post_assign__"
STATIC = "static"
DYNAMIC = "dynamic"
BLUEPRINTS = (STATIC, DYNAMIC)
