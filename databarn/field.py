from __future__ import annotations
from typing import Any

type_ = type


class Field:
    """Seed-Model Field: Field definition for the Seed-like class."""
    label: str  # key for seed.__dna__.label_field_map. It will be set later
    type: type_
    default: Any
    is_key: bool
    auto: bool
    frozen: bool
    none: bool

    def __init__(self, type: type_ | tuple[type_] = object,
                 default: Any = None, key: bool = False,
                 auto: bool = False, none: bool = True,
                 frozen: bool = False):
        if auto and type not in (int, object):
            raise TypeError(
                f"Expected int or object for type arg, but got {type}.")
        self.type = type
        self.default = default
        # is_key to prevent conflict with key, which is used as value throughout the code
        self.is_key = key
        self.auto = auto
        self.frozen = frozen
        self.none = none

    def _set_label(self, label: str) -> None:
        """This will be set in the Dna"""
        self.label = label

    def __repr__(self) -> str:
        """Returns a string representation of the Field.

        "Field(label='my_field', type=int, default=0, key=False, auto=False,
        frozen=False, none=True)"
        """

        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        return "{}({})".format(type(self).__name__, ", ".join(items))


class InstField(Field):
    """Instance Field: Field definition for the seed instance."""
    seed: "Seed"
    was_set: bool
    value: Any  # Get or set the value of the field

    def __init__(self, orig_field: Field, seed: "Seed", label: str, was_set: bool):
        super().__init__(type=orig_field.type, default=orig_field.default,
                         key=orig_field.is_key, auto=orig_field.auto,
                         none=orig_field.none, frozen=orig_field.frozen)
        self._set_label(label)
        self.seed = seed
        self.was_set = was_set

    @property
    def value(self) -> Any:
        """Gets the value of the field at the given moment."""
        return getattr(self.seed, self.label)

    @value.setter
    def value(self, value: Any) -> None:
        """Sets the value of the field.

        Be careful when using this, because it will
        overwrite the value of the field in the seed.
        """
        setattr(self.seed, self.label, value)
