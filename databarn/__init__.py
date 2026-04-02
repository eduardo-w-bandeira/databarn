"""DataBarn public package API.

DataBarn provides:
- Cob: schema-capable in-memory data models,
- Grain: field declarations with constraints,
- Barn: ordered model-aware collections,
- conversion helpers for dict/JSON payloads.
"""

from .cob import Cob
from .grain import Grain
from .barn import Barn
from .funcs import dict_to_cob, json_to_cob
from .decorators import one_to_many_grain, one_to_one_grain
from .exceptions import (
    DataBarnViolationError, DataBarnSyntaxError,
    CobConsistencyError, StaticModelViolationError,
    CobConstraintViolationError, GrainTypeMismatchError,
    GrainLabelError, BarnConstraintViolationError)

__all__ = [
    "Barn",
    "Cob",
    "Grain",
    "BarnConstraintViolationError",
    "CobConsistencyError",
    "CobConstraintViolationError",
    "DataBarnSyntaxError",
    "DataBarnViolationError",
    "GrainLabelError",
    "GrainTypeMismatchError",
    "StaticModelViolationError",
    "dict_to_cob",
    "json_to_cob",
    "one_to_many_grain",
    "one_to_one_grain",
]
