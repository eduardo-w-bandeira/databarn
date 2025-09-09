from __future__ import annotations
from typing import Any, Type


class Grain:
    """Cob-Model Grain: Grain definition for the Cob-like class."""
    label: str # This will be set in the Cob-model dna
    default: Any
    pk: bool
    auto: bool
    frozen: bool
    none: bool
    unique: bool
    key_name: str
    type: Any # This will be set in the Cob-model dna
    model: Type # This will be set in the Cob-model dna
    wiz_child_model: "Cob" | None = None  # This will be set in the Cob-model dna

    # Cob-instance specific attributes
    cob: "Cob" # Bound cob instance
    was_set: bool # This will be set in the cob-instance dna
    value: Any  # Dynamically get or set the value of the grain, only in the cob instance


    def __init__(self, default: Any = None, pk: bool = False, auto: bool = False,
                 none: bool = True, frozen: bool = False, unique: bool = False,
                 key_name: str="", **custom_attrs):
        """Initializes the Grain object.
        
        Args:
            default: The default value of the grain.
            pk: Whether this grain is part of the primary key.
            auto: Whether this grain is auto-incremented.
            none: Whether this grain can be None.
            frozen: Whether this grain is immutable after being set once.
            unique: Whether this grain must be unique across all instances.
            key_name: The key to use when the cob is converted to a dictionary or json.
                If not provided, the label will be used.
            custom_attrs: Any additional custom attributes to set on the Grain instance.
        """
        self.default = default
        self.pk = pk
        self.auto = auto
        self.frozen = frozen
        self.none = none
        self.unique = unique
        self.key_name = key_name
        self.__dict__.update(custom_attrs)

    def _set_model_attrs(self, model: Type, label: str, type: Any) -> None:
        self.model = model
        self.label = label
        if not self.key_name:
            self.key_name = label
        self.type = type

    def _set_cob_attrs(self, cob: "Cob", was_set: bool) -> None:
        """This will be set in the cob-instance

        This method is private solely to hide it from the user.
        """
        self.cob = cob
        self.was_set = was_set

    def _set_key_name(self, key_name: str) -> None:
        """Sets the key_name attribute.

        This method is private solely to hide it from the user.
        """
        self.key_name = key_name

    def _set_wiz_child_model(self, wiz_child_model: "Cob") -> None:
        """Sets the wiz_child_model attribute.

        This method is private solely to hide it from the user.
        """
        self.wiz_child_model = wiz_child_model

    @property
    def value(self) -> Any:
        """Gets the value of the grain at the given moment."""
        return getattr(self.cob, self.label)

    @value.setter
    def value(self, value: Any) -> None:
        """Sets the value of the grain.

        Be careful when using this, because it will
        overwrite the value of the grain in the cob.
        """
        setattr(self.cob, self.label, value)

    def __repr__(self) -> str:
        """Returns a string representation of the Grain.

        F.ex.:
            Grain(label='my_grain', type=int, default=0, pk=False, auto=False,
            frozen=False, none=True)"
        """
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        sep_items = ", ".join(items)
        return f"{type(self).__name__}({sep_items})"
