from __future__ import annotations
import inspect
from typing import Any, Type, Callable
from types import SimpleNamespace as Namespace
from .constants import ABSENT
from .exceptions import CobConsistencyError
from .trails import fo


class Grain:
    """Cob-Model Grain: Grain definition for the Cob-like class."""
    label: str
    type: Type | None
    default: Any
    pk: bool
    auto: bool
    frozen: bool
    required: bool
    unique: bool
    comparable: bool
    key: str
    factory: Callable[[], Any] | None
    parent_model: Type["Cob"] | None  # type: ignore # Will be set later by Dna
    # type: ignore # Will be set later by @one_to_many or @one_to_one_grain
    child_model: Type["Cob"] | None
    is_child_barn: bool
    allows_deletion: bool
    info: Namespace

    def __init__(self, default: Any = None, *, pk: bool = False, required: bool = False,
                 auto: bool = False, frozen: bool = False, unique: bool = False,
                 comparable: bool = False, factory: Callable[[], Any] | None = None,
                 # type: ignore
                 key: str = "", child_model: Type["Cob"] | None = None, **info_kwargs):
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
            infos: Any additional custom attributes to set on the Grain object.
        """
        if auto and default is not None:
            raise CobConsistencyError(
                "A Grain cannot be both auto and have a default value other than None.")
        if default is not None and factory is not None:
            raise CobConsistencyError(
                "A Grain cannot have both a default value and a factory.")
        self.label = ""  # Will be set later by Dna
        self.type = None  # Will be set later by Dna
        self.default = default
        self.pk = pk
        self.required = required
        self.auto = auto
        self.frozen = frozen
        self.unique = unique
        self.comparable = comparable
        self.key = key
        self.factory = factory
        self.parent_model = None  # Will be set later by Dna
        self.child_model = child_model
        self.is_child_barn = False  # Will be set to True by @one_to_many_grain
        # Whether the grain can be deleted from a Cob
        self.allows_deletion = False if (
            pk or frozen or unique or required) else True
        # Store custom attributes in an Info instance
        self.info = Namespace(**info_kwargs)

    def _set_parent_model_metadata(self, parent_model: Type["Cob"] | None,
                                   label: str, type: Any) -> None:
        """parent_model can be None when the grain is created by a decorator,
        because at that moment the outer Cob-model is not yet defined."""
        self.parent_model = parent_model
        self.label = label
        self.type = type

    def _set_child_model(self, child_model: Type["Cob"], is_child_barn: bool) -> None:
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
            Grain(label='my_grain', type=int, default=0, pk=False, auto=False,
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

        def __dir__(self):
            grain_attr_names = dir(self.grain)
            grain_properties = []
            for attr_name in grain_attr_names:
                if not callable(getattr(self.grain, attr_name)) and not attr_name.startswith('__'):
                    grain_properties.append(attr_name)
            # 3. Combine with Grist's own directory
            return sorted(set(super().__dir__()) | set(grain_properties))

        def __getattr__(self, name):
            # Check if the attribute exists on grain
            if hasattr(self.grain, name):
                attr = getattr(self.grain, name)
                # Verify it is not a method/function
                if not callable(attr):
                    return attr

            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}' (or it is a protected method)"
            )

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

    def has_value(self) -> bool:
        """Return True if the attribute exists in the Cob (was not deleted),
        False otherwise."""
        return hasattr(self.cob, self.label)

    def __repr__(self) -> str:
        """Return a string representation of the grist.

        F.ex.:
            Grist(label='number', type=int, default=0, pk=False, auto=False,
            frozen=False, required=True)"
        """
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        sep_items = ", ".join(items)
        return f"{type(self).__name__}({sep_items})"
