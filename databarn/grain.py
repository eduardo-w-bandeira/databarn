from __future__ import annotations
from typing import Any


class Grain:
    """Cob-Model Grain: Grain definition for the Cob-like class."""
    label: str  # key for cob.__dna__.label_grain_map. It will be set later
    default: Any
    is_key: bool
    auto: bool
    frozen: bool
    none: bool
    unique: bool
    type: Any

    def __init__(self, default: Any = None, is_key: bool = False,
                 auto: bool = False, none: bool = True,
                 frozen: bool = False, unique: bool = False):
        self.default = default
        self.is_key = is_key
        self.auto = auto
        self.frozen = frozen
        self.none = none
        self.unique = unique

    def _set_label(self, label: str) -> None:
        """This will be set in the Dna

        This method is private solely to hide it from the user.
        """
        self.label = label

    def _set_type(self, type: Any) -> None:
        """This will be set in the Dna

        This method is private solely to hide it from the user.
        """
        self.type = type

    def __repr__(self) -> str:
        """Returns a string representation of the Grain.

        F.ex.:
            Grain(label='my_grain', type=int, default=0, is_key=False, auto=False,
            frozen=False, none=True)"
        """
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        sep_items = ", ".join(items)
        return f"{type(self).__name__}({sep_items})"


class InstGrain(Grain):
    """Instance Grain: Grain definition for the cob instance."""
    bound_cob: "Cob"
    was_set: bool
    value: Any  # Get or set the value of the grain

    def __init__(self, orig_grain: Grain, bound_cob: "Cob", label: str, type: Any, was_set: bool):
        super().__init__(default=orig_grain.default,
                         is_key=orig_grain.is_key, auto=orig_grain.auto,
                         none=orig_grain.none, frozen=orig_grain.frozen,
                         unique=orig_grain.unique)
        self._set_label(label)
        self._set_type(type)
        self.bound_cob = bound_cob
        self.was_set = was_set

    @property
    def value(self) -> Any:
        """Gets the value of the grain at the given moment."""
        return getattr(self.bound_cob, self.label)

    @value.setter
    def value(self, value: Any) -> None:
        """Sets the value of the grain.

        Be careful when using this, because it will
        overwrite the value of the grain in the cob.
        """
        setattr(self.bound_cob, self.label, value)
