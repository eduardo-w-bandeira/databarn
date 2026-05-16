from __future__ import annotations
from collections.abc import Callable
from typing import Any
from types import SimpleNamespace
from .constants import ABSENT, MISSING_ARG
from .exceptions import SchemaViolationError
from .trails import fo, classmethod_only
from .exceptions import DataBarnSyntaxError

_type = type

class GrainMeta(_type):
    """Metaclass used to customize class-level Grain representation."""

    def __repr__(klass) -> str:
        """Return a concise representation of Grain classes."""
        keys = (
            "label",
            "type",
            "default",
            "pk",
            "required",
            "autoenum",
            "frozen",
            "unique",
            "comparable",
            "key",
            "factory",
            "parent_model",
            "child_model",
            "is_child_barn",
            "info",
        )
        attrs = {key: getattr(klass, key)
                 for key in keys if hasattr(klass, key)}
        formatted_items = ", ".join(f"{k}={v!r}" for k, v in attrs.items())
        return f"{klass.__name__}<{formatted_items}>"

class BaseGrain(metaclass=GrainMeta):
    """Model-level field definition used by Cob classes."""
    label: str
    type: _type | None
    default: Any
    pk: bool
    autoenum: bool
    frozen: bool
    required: bool
    unique: bool
    comparable: bool
    key: str
    factory: Callable[[], Any] | None
    parent_model: _type["Cob"]  # Will be set later by Dna
    # Will be set later by relationship decorators
    child_model: _type["Cob"]  # type: ignore
    is_child_barn: bool
    info: SimpleNamespace
    # Instance-level grain attributes
    cob: "Cob"  # type: ignore

    @classmethod_only
    def __setup__(klass, parent_model: _type["Cob"],
                  label: str, type: Any) -> None:
        """Set up the minimum required metadata for a Grain,
        called during model setup.

        `parent_model` may be `None` temporarily when relationship
        decorators create grains before the outer model class exists.
        """
        klass.parent_model = parent_model
        klass.label = label
        klass.type = type
        klass._validate()

    @classmethod
    def _validate(klass) -> None:
        assert hasattr(klass, "parent_model"), "'parent_model' must be set."
        assert hasattr(klass, "label"), "'label' must be set."
        assert hasattr(klass, "type"), "'type' must be set."
        if klass.autoenum:
            # type: ignore[arg-type]
            if not (isinstance(klass.type, _type) and issubclass(klass.type, int)):
                raise DataBarnSyntaxError(fo(f"""
                    The Grain '{klass.label}' was defined as 'autoenum=True',
                    but was type annotated as {klass.type}.
                    'autoenum' only works with 'int' or compatible types."""))

    @classmethod_only
    def _set_relationship_data(klass, label: str, type: Any,
                               child_model: _type["Cob"],
                               is_child_barn: bool) -> None:
        """Set up the data for relationship Grains, called by relationship decorators."""
        klass.label = label
        klass.type = type
        klass.child_model = child_model
        klass.is_child_barn = is_child_barn

    @classmethod_only
    def set_key(klass, key: str) -> None:
        """Set the serialized key name used by ``to_dict``/``to_json``."""
        klass.key = key

    # Instance-level methods
    def __init__(self, cob: "Cob") -> None:  # type: ignore
        self.cob = cob

    def get_value(self, default: Any = MISSING_ARG) -> Any:
        """Get the value of the Grain at the given moment."""
        if default is MISSING_ARG:
            return getattr(self.cob, self.label)
        return getattr(self.cob, self.label, default)

    def set_value(self, value: Any) -> None:
        """Set the value of the Grain in the Cob."""
        setattr(self.cob, self.label, value)

    def attr_exists(self) -> bool:
        """Return True if the attribute exists in the Cob,
        i.e. it has been set or has not been deleted.
        Return False otherwise."""
        return self.label in self.cob.__dict__

    def __repr__(self) -> str:
        """Return a string representation of the Grain.

        F.ex.:
            Grain(label='my_grain', type=int, default=0, pk=False, autoenum=False,
            frozen=False, none=True)"
        """
        attrname_value_map = {}
        for key in self.__annotations__.keys():
            if not key.startswith("_") and hasattr(self, key):
                attrname_value_map[key] = getattr(self, key)
        attrname_value_map["get_value()"] = self.get_value(default=ABSENT)
        k_equal_v = [f"{k}={v!r}" for k, v in attrname_value_map.items()]
        sep_items = ", ".join(k_equal_v)
        return f"{_type(self).__name__}({sep_items})"


def create_grain_class(default: Any = MISSING_ARG, *, pk: bool = False, required: bool = False,
                       autoenum: bool = False, frozen: bool = False, unique: bool = False,
                       comparable: bool = False, factory: Callable[[], Any] | None = None,
                       key: str = "", child_model: _type["Cob"] | None = None,
                       info: dict[str, Any] | None = None) -> _type[BaseGrain]:

    # Capture all args
    argname_val_map = locals()

    if default is not MISSING_ARG and factory is not None:
        raise SchemaViolationError(
            "A Grain cannot have both a default value and a factory.")

    # Handle the specific transformation for 'info'
    info_val = argname_val_map.pop("info")

    # Define the internal attrs
    attrname_val_map = {
        "label": "",
        "type": None,
        "parent_model": None,
        "is_child_barn": False,
        "info": SimpleNamespace(**(info_val or {})), }

    # Merge args and internal attrs
    attrname_val_map.update(argname_val_map)

    return GrainMeta("Grain", (BaseGrain,), attrname_val_map)
