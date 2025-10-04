from __future__ import annotations
from typing import Any, Type
from .trails import NOT_SET


class Info:
    """A mixin class to allow custom attributes on Grain."""

    def __init__(self, **info_kwargs):
        self.__dict__.update(info_kwargs)

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        sep_items = ", ".join(items)
        return f"{type(self).__name__}({sep_items})"


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
    info: Info

    def __init__(self, default: Any = None, *, pk: bool = False, required: bool = False,
                 auto: bool = False, frozen: bool = False, unique: bool = False,
                 comparable: bool = False, key_name: str = "", **info_kwargs):
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
            infos: Any additional custom attributes to set on the Grain object.
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
        self.pre_value = NOT_SET
        # Store custom attributes in an Info instance
        self.info = Info(**info_kwargs)

    def _set_model_attrs(self, model: Type["Cob"] | None, label: str, type: Any) -> None:
        """model can be None when the grain is created by a decorator,
        because at that moment the outer Cob-model is not yet defined."""
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
    """A Seed() is just a bound Grain() to a Cob().
    It allows access to the grain's attributes and methods,
    while being bound to a specific cob instance.
    It is used to get and set the value of the grain in the cob,
    and to check if the grain has been set."""

    # Cob-object specific attributes
    grain: Grain  # Bound grain object
    cob: "Cob"  # Bound cob object
    has_been_set: bool  # @property

    def __init__(self, grain: Grain, cob: "Cob", init_with_sentinel: bool) -> None:
        """Initialize the Seed object.
        Args:
            cob: The Cob object.
            grain: The Grain object.
            init_with_sentinel:
                If true, the grain value will be initially set to sentinel,
                so later it be checked if it has been assigned a value or not.
        """
        self.grain = grain
        self.cob = cob
        if init_with_sentinel:
            self.force_set_value(NOT_SET)

    def __getattribute__(self, name):
        grain = super().__getattribute__('grain')
        if not name.startswith('_') and name in grain.__dict__:
            return getattr(grain, name)
        return super().__getattribute__(name)

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
        and bypass any checks like type, frozen, unique, etc.
        """
        object.__setattr__(self.cob, self.label, value)

    @property
    def has_been_set(self) -> bool:
        """Return True if a value has been assigned to the grain, False otherwise."""
        if self.get_value() is NOT_SET:
            return False
        return True

    def __repr__(self) -> str:
        """Return a string representation of the seed.

        F.ex.:
            Seed(label='number', type=int, default=0, pk=False, auto=False,
            frozen=False, required=True)"
        """
        map = self.grain.__dict__.copy()
        for key, value in self.__dict__.items():
            # Add Seed attributes, just in case.
            map[key] = value
        get_value_meth_name = self.get_value.__name__ + "()"  # 'get_value()'
        map[get_value_meth_name] = self.get_value()
        map["has_been_set"] = self.has_been_set
        items = [f"{k}={v!r}" for k, v in map.items()]
        sep_items = ", ".join(items)
        return f"{type(self).__name__}({sep_items})"
