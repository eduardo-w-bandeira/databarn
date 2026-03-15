from __future__ import annotations
from collections.abc import Callable
from typing import Any
from types import SimpleNamespace as Namespace
from .constants import ABSENT
from .exceptions import CobConsistencyError
from .trails import fo


class Grain:
    """Cob-Model Grain: Grain definition for the Cob-like class."""
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
    deletable: bool
    info: Namespace

    def __init__(self, default: Any = ABSENT, *, pk: bool = False, required: bool = False,
                 autoenum: bool = False, frozen: bool = False, unique: bool = False,
                 comparable: bool = False, factory: Callable[[], Any] | None = None,
                 key: str = "", child_model: type["Cob"] | None = None,
                 deletable: bool = True, **info_kwargs):
        """Initialize the Grain object.

        Args:
            default: The default value of the grain.
            pk: Whether this grain is part of the primary key.
            auto: Whether this grain is auto-incremented.
            required: Whether this grain can be None.
            frozen: Whether this grain is immutable after being set once.
            unique: Whether this grain must be unique across all objects.
            comparable:
                Whether this grain should be included in comparison operations,
                like __eq__ and __lt__. Default is False.
            factory: A callable that returns a default value for the grain.
            key: The key to use when the cob is converted to a dictionary or json.
                If not provided, the label will be used.
            child_model: The child Cob-model for one-to-many or one-to-one relationships.
            deletable: Whether the grain can be deleted from a Cob.
            infos: Any additional custom attributes to set on the Grain object.
        """
        if default is not ABSENT and factory is not None:
            raise CobConsistencyError(
                "A Grain cannot have both a default value and a factory.")
        self.label = ""  # Will be set later by Dna
        self.type = None  # Will be set later by Dna
        self.default = default
        self.pk = pk
        self.required = required
        self.autoenum = autoenum
        self.frozen = frozen
        self.unique = unique
        self.comparable = comparable
        self.key = key
        self.factory = factory
        self.parent_model = None  # Will be set later by Dna
        self.child_model = child_model
        self.is_child_barn = False  # Will be set to True by @one_to_many_grain
        # Whether the grain can be deleted from a Cob
        self.deletable = deletable
        # Store custom attributes in an Info instance
        self.info = Namespace(**info_kwargs)

    def _set_parent_model_metadata(self, parent_model: type["Cob"] | None,
                                   label: str, type: Any) -> None:
        """parent_model can be None when the grain is created by a decorator,
        because at that moment the outer Cob-model is not yet defined."""
        self.parent_model = parent_model
        self.label = label
        self.type = type

    def _set_child_model(self, child_model: type["Cob"], is_child_barn: bool) -> None:
        """Set the model attribute to the child Cob-model.

        This method is used by the one_to_many_grain decorator.
        """
        self.child_model = child_model
        self.is_child_barn = is_child_barn

    def set_key(self, key: str) -> None:
        """Set the key attribute.

        This method can be used on the fly, but should be done with care,
        preferably before the cob object is used.
        """
        self.key = key

    def __repr__(self) -> str:
        """Return a string representation of the Grain.

        F.ex.:
            Grain(label='my_grain', type=int, default=0, pk=False, autoenum=False,
            frozen=False, none=True)"
        """
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        sep_items = ", ".join(items)
        return f"{type(self).__name__}({sep_items})"


class Grist:
    """A Grist is just a Grain bound to a Cob.
    It also allows access to the grain's attributes,
    while being bound to a specific Cob instance.
    It is used to get and set the value of the Grain in the Cob,
    and to check if the Grain has been set."""

    grain: Grain
    cob: "Cob"  # type: ignore

    def __init__(self, grain: Grain, cob: "Cob") -> None:  # type: ignore
        """Initialize the Grist object.
        Args:
            grain: The Grain object.
            cob: The Cob object bound to the Grain.
        """
        self.grain = grain
        self.cob = cob

    def _get_merged_attrs_map(self, include_self_methods=True) -> list[str]:
        filtered_attr_names = []
        for attr_name in self.grain.__annotations__.keys():
            if not attr_name.startswith('_'):
                filtered_attr_names.append(attr_name)
        for attr_name in super().__dir__():
            if attr_name in filtered_attr_names:
                continue
            if not include_self_methods and callable(getattr(self, attr_name)):
                continue
            filtered_attr_names.append(attr_name)
        filtered_attr_names.sort()
        name_value_map = {name: getattr(self, name) for name in filtered_attr_names}
        return name_value_map

    def __dir__(self):
        return list(self._get_merged_attrs_map().keys())

    def __getattr__(self, name):
        # Check if the attribute exists on grain
        if name in self.grain.__annotations__ and not name.startswith('_'):
            return getattr(self.grain, name)
        raise AttributeError(fo(f"""
            '{type(self).__name__}' object has no attribute '{name}'"""))

    def get_value(self, default=ABSENT) -> Any:
        """Get the value of the Grain at the given moment."""
        if default is ABSENT:
            return getattr(self.cob, self.label)
        return getattr(self.cob, self.label, default)

    def get_value_or_none(self) -> Any:
        """Get the value of the Grain, or None if it does not exist."""
        return getattr(self.cob, self.label, None)

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
        """Return a string representation of the grist.

        F.ex.:
            Grist(label='number', type=int, default=0, pk=False, autoenum=False,
            frozen=False, required=True)"
        """
        attr_name_value_map = self._get_merged_attrs_map(include_self_methods=False)
        items = [f"{k}={v!r}" for k, v in attr_name_value_map.items()]
        sep_items = ", ".join(items)
        return f"{type(self).__name__}({sep_items})"
