from __future__ import annotations
from collections.abc import Callable
from typing import Any
from types import SimpleNamespace
from .constants import ABSENT
from .exceptions import CobConsistencyError
from .trails import fo, classmethod_only


class BaseGrain:
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

    # Instance-level methods

    def __init__(self, cob: "Cob") -> None:  # type: ignore
        self.cob = cob

    def get_value(self, default: Any = ABSENT) -> Any:
        """Get the value of the Grain at the given moment."""
        if default is ABSENT:
            return getattr(self.cob, self.label)
        return getattr(self.cob, self.label, default)

    def get_value_or_none(self) -> Any:
        """Return the current value, or None when the attribute is unset."""
        return self.get_value(default=None)

    def set_value(self, value: Any) -> None:
        """Set the value of the Grain in the Cob."""
        setattr(self.cob, self.label, value)

    def force_set_value(self, value: Any) -> None:
        """Force set the value of the Grain, bypassing any checks.

        Be very careful when using this, because it will
        overwrite the value of the Grain in the Cob,
        and bypass any checks like type, frozen, unique, etc.
        """
        object.__setattr__(self.cob, self.label, value)

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
        items = [f"{k}={v!r}" for k, v in attrname_value_map.items()]
        sep_items = ", ".join(items)
        return f"{type(self).__name__}({sep_items})"


def create_grain_class(default: Any = ABSENT, *, pk: bool = False, required: bool = False,
                       autoenum: bool = False, frozen: bool = False, unique: bool = False,
                       comparable: bool = False, factory: Callable[[], Any] | None = None,
                       key: str = "", child_model: type["Cob"] | None = None,
                       info: dict[str, Any] | None = None) -> type[BaseGrain]:
    """Factory function to create a Grain with the given parameters."""

    if default is not ABSENT and factory is not None:
        raise CobConsistencyError(
            "A Grain cannot have both a default value and a factory.")

    class Grain(BaseGrain):
        label = ""  # Will be set later by Dna
        type = None  # Will be set later by Dna
        default = default
        pk = pk
        required = required
        autoenum = autoenum
        frozen = frozen
        unique = unique
        comparable = comparable
        key = key
        factory = factory
        parent_model = None  # Will be set later by Dna
        child_model = child_model
        is_child_barn = False  # Will be set to True by @one_to_many_grain
        # Store custom attributes in an Info instance
        info = SimpleNamespace(**(info or {}))

    return Grain
