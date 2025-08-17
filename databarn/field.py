from __future__ import annotations
from typing import Any


class Field:
    """Seed-Model Field: Field definition for the Seed-like class."""
    label: str  # key for seed.__dna__.label_field_map. It will be set later
    default: Any
    is_key: bool
    auto: bool
    frozen: bool
    none: bool
    unique: bool
    type: Any

    def __init__(self, default: Any = None, key: bool = False,
                 auto: bool = False, none: bool = True,
                 frozen: bool = False, unique: bool = False):
        # if auto and type not in (int, object):
        #     raise TypeError(
        #         f"Expected int or object for type arg, but got {type}.")
        self.default = default
        # is_key to prevent conflict with key, which is used as value throughout the code
        self.is_key = key
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
        """Returns a string representation of the Field.

        F.ex.:
            Field(label='my_field', type=int, default=0, key=False, auto=False,
            frozen=False, none=True)"
        """
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        sep_items = ", ".join(items)
        return f"{type(self).__name__}({sep_items})"


class InstField(Field):
    """Instance Field: Field definition for the seed instance."""
    bound_seed: "Seed"
    was_set: bool
    value: Any  # Get or set the value of the field

    def __init__(self, orig_field: Field, bound_seed: "Seed", label: str, type: Any, was_set: bool):
        super().__init__(default=orig_field.default,
                         key=orig_field.is_key, auto=orig_field.auto,
                         none=orig_field.none, frozen=orig_field.frozen,
                         unique=orig_field.unique)
        self._set_label(label)
        self._set_type(type)
        self.bound_seed = bound_seed
        self.was_set = was_set

    @property
    def value(self) -> Any:
        """Gets the value of the field at the given moment."""
        return getattr(self.bound_seed, self.label)

    @value.setter
    def value(self, value: Any) -> None:
        """Sets the value of the field.

        Be careful when using this, because it will
        overwrite the value of the field in the seed.
        """
        setattr(self.bound_seed, self.label, value)
