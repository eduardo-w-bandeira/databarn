from __future__ import annotations
from collections.abc import Callable
from typing import Any
from types import SimpleNamespace
from .constants import MISSING_ARG
from .exceptions import CobConsistencyError
from .trails import fo, classmethod_only
from .exceptions import DataBarnSyntaxError


class GrainMeta(type):
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
        attrs = {key: getattr(klass, key) for key in keys if hasattr(klass, key)}
        formatted_items = ", ".join(f"{k}={v!r}" for k, v in attrs.items())
        return f"{klass.__name__}<{formatted_items}>"


class BaseGrain(metaclass=GrainMeta):
    """Model-level field definition used by Cob classes."""
    label: str
    type: type | None
    default: Any
    pk: bool
    autoenum: bool
    frozen: bool
    required: bool
    unique: bool
    comparable: bool
    key: str
    factory: Callable[[], Any] | None
    parent_model: type["Cob"] | None  # type: ignore # Will be set later by Dna
    # type: ignore # Will be set later by @one_to_many or @one_to_one_grain
    child_model: type["Cob"] | None
    is_child_barn: bool
    info: SimpleNamespace
    # Instance-level grist attributes
    cob: "Cob"  # type: ignore

    @classmethod_only
    def _set_parent_model_metadata(klass, parent_model: type["Cob"] | None,
                                   label: str, type: Any) -> None:
        """Attach parent model metadata resolved during model setup.

        ``parent_model`` may be ``None`` temporarily when relationship
        decorators create grains before the outer model class exists.
        """
        klass.parent_model = parent_model
        klass.label = label
        klass.type = type

    @classmethod_only
    def _set_child_model(klass, child_model: type["Cob"], is_child_barn: bool) -> None:
        """Store child model metadata for relationship grains."""
        klass.child_model = child_model
        klass.is_child_barn = is_child_barn

    @classmethod_only
    def set_key(klass, key: str) -> None:
        """Set the serialized key name used by ``to_dict``/``to_json``."""
        klass.key = key

    @classmethod_only
    def _validate(klass) -> None:
        if klass.autoenum:
            if not (isinstance(klass.type, type) and issubclass(klass.type, int)):  # type: ignore[arg-type]
                raise DataBarnSyntaxError(fo(f"""
                    The Grain '{klass.label}' was defined as 'autoenum=True',
                    but was type annotated as {klass.type}.
                    'autoenum' only works with 'int' or compatible types."""))


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
        """Return True if the attribute exists in the Cob (was not deleted),
        False otherwise."""
        return hasattr(self.cob, self.label)

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
        attrname_value_map["get_value()"] = self.get_value(default="<UNSET>")
        k_equal_v = [f"{k}={v!r}" for k, v in attrname_value_map.items()]
        sep_items = ", ".join(k_equal_v)
        return f"{type(self).__name__}({sep_items})"


def create_grain_class(default: Any = MISSING_ARG, *, pk: bool = False, required: bool = False,
                       autoenum: bool = False, frozen: bool = False, unique: bool = False,
                       comparable: bool = False, factory: Callable[[], Any] | None = None,
                       key: str = "", child_model: type["Cob"] | None = None,
                       info: dict[str, Any] | None = None) -> type[BaseGrain]:
    
    # Capture all args
    argname_val_map = locals()

    if default is not MISSING_ARG and factory is not None:
        raise CobConsistencyError("A Grain cannot have both a default value and a factory.")

    # Handle the specific transformation for 'info'
    info_val = argname_val_map.pop("info")
    
    # Define the internal attrs
    attrname_val_map = {
        "label": "",
        "type": None,
        "parent_model": None,
        "is_child_barn": False,
        "info": SimpleNamespace(**(info_val or {})),}

    # Merge args and internal attrs
    attrname_val_map.update(argname_val_map)

    return GrainMeta("Grain", (BaseGrain,), attrname_val_map)