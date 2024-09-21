from __future__ import annotations
from .field import Field, InstField
from typing import Any, Type

LazyBarn = None
LazySeed = None


class Dna:
    # seed model
    label_field_map: dict
    key_fields: list
    is_comp_key: bool
    key_defined: bool
    keyring_len: int
    dynamic: bool
    # seed instance
    seed: "Seed" | None
    autoid: int | None
    keyring: Any | tuple[Any]
    barns: set

    def __init__(self, seed_model: Type["Seed"], seed: "Seed" | None = None):
        """Initialize the Meta object.

        Args:
            seed_model: The Seed-like class.
            seed: The Seed instance. If provided, it assumes this is for a seed instance.
        """
        self.seed = seed
        self.key_fields = []
        self.label_field_map = {}
        for name, value in seed_model.__dict__.items():
            if not isinstance(value, Field):
                continue
            label = name
            field = value
            field._set_label(label)
            if seed:
                # Update the field with the seed instance
                field = InstField(orig_field=field, seed=seed,
                                  label=label, was_set=False)
            if field.is_key:
                self.key_fields.append(field)
            self.label_field_map.update({label: field})
        self.dynamic = False if self.label_field_map else True
        self.key_defined = len(self.key_fields) > 0
        self.is_comp_key = len(self.key_fields) > 1
        self.keyring_len = len(self.key_fields) or 1
        # If the key is not provided, autoid will be used as key
        self.autoid = None
        self.barns = set()

    def _create_dynamic_field(self, label: str):
        """Adds a dynamic field to the Meta object.

        Args:
            label: The label of the dynamic field to add
        """
        assert self.dynamic is True
        field = InstField(orig_field=Field(), seed=self.seed,
                          label=label, was_set=False)
        self.label_field_map.update({label: field})
        return field

    @property
    def keyring(self) -> Any | tuple[Any]:
        """Returns the keyring of the Seed instance.

        The keyring is either a key or a tuple of keys. If the Meta
        object has no key labels, the autoid is returned instead.

        Returns:
            tuple[Any] or Any: The keyring of the Seed instance
        """
        if not self.key_defined:
            return self.autoid
        keys = tuple(field.value for field in self.key_fields)
        if len(keys) == 1:
            return keys[0]
        return keys

    def seed_to_dict(self) -> dict[str, Any]:
        """Converts the seed to a dictionary.

        Recursively processes the seeds in the fields of the seed,
        and returns a dictionary with the label as the key and the value as the
        value. If the value is a Barn or a Seed, it is recursively processed.

        Returns:
            dict[str, Any]: The dictionary representation of the Seed instance
        """
        global LazyBarn, LazySeed
        if not LazyBarn:
            from .barn import Barn as LazyBarn
        if not LazySeed:
            from .seed import Seed as LazySeed
        label_value_map = {}
        for label, value in self.label_field_map.items():
            # If value is a barn or a seed, recursively process its seeds
            if isinstance(value, LazyBarn):
                label_value_map[label] = value.__dna__.seed_to_dict()
            else:
                label_value_map[label] = value
        return label_value_map
