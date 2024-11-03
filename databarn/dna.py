from __future__ import annotations
from .field import Field, InstField
from typing import Any, Type


class Dna:

    # seed model
    label_to_field: dict
    key_fields: list
    is_compos_key: bool
    key_defined: bool
    keyring_len: int
    dynamic: bool
    parent: "Seed" | None = None

    # seed instance
    bound_seed: "Seed" | None
    autoid: int | None
    keyring: Any | tuple[Any]
    barns: set

    def __init__(self, model: Type["Seed"], bound_seed: "Seed" | None = None):
        """Initializes the Meta object.

        Args:
            model: The Seed-like class.
            seed: The seed instance. If provided, it assumes this is for a seed instance.
        """
        self.model = model
        self.bound_seed = bound_seed
        self.key_fields = []
        self.label_to_field = {}
        for name, value in model.__dict__.items():
            if not isinstance(value, Field):
                continue
            field = self._set_up_field(value, name)
            if field.is_key:
                self.key_fields.append(field)
            self.label_to_field.update({field.label: field})
        self.dynamic = False if self.label_to_field else True
        self.key_defined = len(self.key_fields) > 0
        self.is_compos_key = len(self.key_fields) > 1
        self.keyring_len = len(self.key_fields) or 1
        # If the key is not provided, autoid will be used as key
        self.autoid = None
        self.barns = set()

    def _set_up_field(self, field: Field, label: str) -> None:
        field._set_label(label)
        if label in self.model.__annotations__:
            tipe = self.model.__annotations__[label]
        else:
            tipe = Any
        field._set_type(tipe)
        if self.bound_seed:
            # Update the field with the seed instance
            field = InstField(orig_field=field, bound_seed=self.bound_seed,
                              label=label, type=tipe, was_set=False)
        return field

    def _set_parent_if(self, field: InstField):
        # Lazy import to avoid circular imports
        from .barn import Barn
        from .seed import Seed
        if isinstance(field.value, Barn):
            for child in field.value:
                child.__dna__.parent = self.bound_seed
        elif isinstance(field.value, Seed):
            field.value.__dna__.parent = self.bound_seed

    def _create_dynamic_field(self, label: str) -> InstField:
        """Adds a dynamic field to the Meta object.

        Args:
            label: The label of the dynamic field to add

        This method is private solely to hide it from the user,
        but it will be called by the seed when a dynamic field is created.
        """
        field = InstField(orig_field=Field(), bound_seed=self.bound_seed,
                          label=label, type=Any, was_set=False)
        self.label_to_field.update({label: field})
        return field

    @property
    def keyring(self) -> Any | tuple[Any]:
        """Returns the keyring of the seed.

        The keyring is either a key or a tuple of keys. If the
        key-field is not defined, the autoid is returned instead.

        Returns:
            tuple[Any] or Any: The keyring of the seed
        """
        if not self.key_defined:
            return self.autoid
        keys = tuple(field.value for field in self.key_fields)
        if not self.is_compos_key:
            return keys[0]
        return keys

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of the seed.

        Every sub-Barn is converted into a list of seeds,
        which are then converted to dictionaries recursively.
        Every sub-seed is converted to a dictionary too.

        Returns:
            A dictionary representation of the seed
        """
        # Lazy import to avoid circular imports
        from .barn import Barn
        from .seed import Seed
        label_to_value = {}
        for label, field in self.label_to_field.items():
            # If value is a barn or a seed, recursively process its seeds
            if isinstance(field.value, Barn):
                barn = field.value
                seeds = [seed.__dna__.to_dict() for seed in barn]
                label_to_value[label] = seeds
            elif isinstance(field.value, Seed):
                seed = field.value
                label_to_value[label] = seed.__dna__.to_dict()
            else:
                label_to_value[label] = field.value
        return label_to_value
