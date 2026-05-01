"""DataBarn public package API.

DataBarn provides:
- Cob: schema-capable in-memory data models,
- Grain: field declarations with constraints,
- Barn: ordered model-aware collections,
- conversion helpers for dict/JSON payloads.
"""

from .cob import Cob
from .grain import create_grain_class as Grain
from .barn import Barn
from .funcs import dict_to_cob, json_to_cob
from .decorators import (
    one_to_many_grain, one_to_one_grain,
    post_init, before_assign, after_assign)
from .exceptions import (
    DataBarnViolationError,  ValidationError,
    DataBarnSyntaxError, CobConsistencyError,
    SchemeViolationError, CobConstraintViolationError,
    GrainTypeMismatchError, GrainLabelError,
    BarnConstraintViolationError)

__version__ = "1.10.1"

__all__ = [
    "Barn",
    "Cob",
    "__version__",
    "Grain",
    "BarnConstraintViolationError",
    "CobConsistencyError",
    "CobConstraintViolationError",
    "DataBarnSyntaxError",
    "DataBarnViolationError",
    "ValidationError",
    "GrainLabelError",
    "GrainTypeMismatchError",
    "SchemeViolationError",
    "dict_to_cob",
    "json_to_cob",
    "post_init",
    "one_to_many_grain",
    "one_to_one_grain",
    "before_assign",
    "after_assign",
]
