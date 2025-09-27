from __future__ import annotations
from typing import Any, Type, get_type_hints
from .trails import sentinel
from .exceptions import DataBarnViolationError

class _CustomGrainAttrs:
    """A mixin class to allow custom attributes on Grain."""

    def __init__(self, **custom_attrs):
        self.__dict__.update(custom_attrs)


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
    key_name: str
    model: Type["Cob"] | None
    pre_value: Any
    custom: _CustomGrainAttrs

    def __init__(self, default: Any = None, pk: bool = False, required: bool = False,
                 auto: bool = False, frozen: bool = False, unique: bool = False,
                 comparable: bool = False, key_name: str = "", **custom_attrs):
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
            key_name: The key to use when the cob is converted to a dictionary or json.
                If not provided, the label will be used.
            custom_attrs: Any additional custom attributes to set on the Grain object.
        """
        self.label = ""  # This will be set in the Cob-model dna
        self.type = None  # This will be set in the Cob-model dna
        self.default = default
        self.pk = pk
        self.required = required
        self.auto = auto
        self.frozen = frozen
        self.unique = unique
        self.comparable = comparable
        self.key_name = key_name
        self.model = None  # This will be set in the Cob-model dna
        self.pre_value = sentinel
        self.custom = _CustomGrainAttrs(**custom_attrs)

    def _set_model_attrs(self, model: Type, label: str, type: Any) -> None:
        self.model = model
        self.label = label
        self.type = type

    def set_key_name(self, key_name: str) -> None:
        """Set the key_name attribute.

        This method can be used on the fly, but should be done with care,
        preferably before the cob object is used.
        """
        self.key_name = key_name

    def _set_pre_value(self, pre_value: Any) -> None:
        """Set the pre_value attribute.

        This method is private solely to hide it from the user.
        """
        self.pre_value = pre_value

    def __repr__(self) -> str:
        """Return a string representation of the Grain.

        F.ex.:
            Grain(label='my_grain', type=int, default=0, pk=False, auto=False,
            frozen=False, none=True)"
        """
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        sep_items = ", ".join(items)
        return f"{type(self).__name__}({sep_items})"


class Seed:

    # Cob-object specific attributes
    cob: "Cob"  # Bound cob object
    has_been_set: bool # @property
    grain: Grain  # Bound grain object

    def __init__(self, cob: "Cob", grain: Grain):
        """Initialize the Seed object.
        Args:
            cob: The Cob object.
            grain: The Grain object.
        """
        for name, value in grain.__dict__.items():
            # To show up in repr(), dir(), help(), etc.
            object.__setattr__(self, name, value)
        self.cob = cob
        self.grain = grain

    def __getattribute__(self, name):
        grain = super().__getattribute__('grain')
        if not name.startswith('_') and name in grain.__dict__:
            value = getattr(grain, name)
            object.__setattr__(self, name, value)  # Cache it for caution
            return value
        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        raise DataBarnViolationError("Setting attributes on Seed is not allowed.")

    def get_value(self) -> Any:
        """Get the value of the grain at the given moment."""
        return getattr(self.cob, self.label)

    def set_value(self, value: Any) -> None:
        """Set the value of the grain in the cob."""
        setattr(self.cob, self.label, value)

    def force_set_value(self, value: Any) -> None:
        """Force set the value of the grain, bypassing any checks.

        Be very careful when using this, because it will
        overwrite the value of the grain in the cob,
        and bypass any checks like frozen, type, etc.
        """
        object.__setattr__(self.cob, self.label, value)

    @property
    def has_been_set(self) -> bool:
        """Return True if a value has been assigned to the grain, False otherwise."""
        if self.get_value() is not sentinel:
            return True
        return False

    def __repr__(self) -> str:
        """Return a string representation of the seed.

        F.ex.:
            Seed(label='number', type=int, default=0, pk=False, auto=False,
            frozen=False, required=True)"
        """
        map = self.grain.__dict__.copy()
        for key, value in self.__dict__.items():
            if key not in map:
                map[key] = value
        has_been_set_name = self.has_been_set.__name__
        map[has_been_set_name] = self.has_been_set
        items = [f"{k}={v!r}" for k, v in map.items()]
        sep_items = ", ".join(items)
        return f"{type(self).__name__}({sep_items})"
