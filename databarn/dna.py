from __future__ import annotations
from .grain import Grain, InstGrain
from typing import Any, Type


class Dna:

    # cob model
    label_grain_map: dict
    key_grains: list
    is_compos_key: bool
    key_defined: bool
    keyring_len: int
    dynamic: bool
    parent: "Cob" | None = None

    # cob instance
    bound_cob: "Cob" | None
    autoid: int | None
    keyring: Any | tuple[Any]
    barns: set

    def __init__(self, model: Type["Cob"], bound_cob: "Cob" | None = None):
        """Initializes the Meta object.

        Args:
            model: The Cob-like class.
            cob: The cob instance. If provided, it assumes this is for a cob instance.
        """
        self.model = model
        self.bound_cob = bound_cob
        self.key_grains = []
        self.label_grain_map = {}
        for name, value in list(model.__dict__.items()):
            # `list()` was used in the loop because,
            # during class building in `new_class.__dna__ = Dna(new_class)`,
            # it was rasing "RuntimeError: dictionary changed size during iteration",
            # if type was not annotated for the grain.
            if not isinstance(value, Grain):
                continue
            grain = self._set_up_grain(value, name)
            if grain.is_key:
                self.key_grains.append(grain)
            self.label_grain_map.update({grain.label: grain})
        self.dynamic = False if self.label_grain_map else True
        self.key_defined = len(self.key_grains) > 0
        self.is_compos_key = len(self.key_grains) > 1
        self.keyring_len = len(self.key_grains) or 1
        # If the key is not provided, autoid will be used as key
        self.autoid = None
        self.barns = set()

    def _set_up_grain(self, grain: Grain, label: str) -> None:
        grain._set_label(label)
        if label in self.model.__annotations__:
            tipe = self.model.__annotations__[label]
        else:
            tipe = Any
        grain._set_type(tipe)
        if self.bound_cob:
            # Update the grain with the cob instance
            grain = InstGrain(orig_grain=grain, bound_cob=self.bound_cob,
                              label=label, type=tipe, was_set=False)
        return grain

    def _set_parent_if(self, grain: InstGrain):
        # Lazy import to avoid circular imports
        from .barn import Barn
        from .cob import Cob
        if isinstance(grain.value, Barn):
            for child in grain.value:
                child.__dna__.parent = self.bound_cob
        elif isinstance(grain.value, Cob):
            grain.value.__dna__.parent = self.bound_cob

    def _create_dynamic_grain(self, label: str) -> InstGrain:
        """Adds a dynamic grain to the Meta object.

        Args:
            label: The label of the dynamic grain to add

        This method is private solely to hide it from the user,
        but it will be called by the cob when a dynamic grain is created.
        """
        grain = InstGrain(orig_grain=Grain(), bound_cob=self.bound_cob,
                          label=label, type=Any, was_set=False)
        self.label_grain_map.update({label: grain})
        return grain

    @property
    def keyring(self) -> Any | tuple[Any]:
        """Returns the keyring of the cob.

        The keyring is either a key or a tuple of keys. If the
        key-grain is not defined, the autoid is returned instead.

        Returns:
            tuple[Any] or Any: The keyring of the cob
        """
        if not self.key_defined:
            return self.autoid
        keys = tuple(grain.value for grain in self.key_grains)
        if not self.is_compos_key:
            return keys[0]
        return keys

    @property
    def grains(self) -> list[InstGrain]:
        """Returns a list of the cob's grains."""
        return list(self.label_grain_map.values())

    def copy(self) -> "Cob":
        """Returns a copy of the cob instance."""
        from .barn import Barn
        from .cob import Cob
        label_value_map = {}
        for grain in self.label_grain_map.values():
            new_value = grain.value
            if isinstance(grain.value, Barn):
                new_value = Barn(grain.value.model)
                [new_value.append(cob.__dna__.copy()) for cob in grain.value]
            elif isinstance(grain.value, Cob):
                new_value = grain.value.__dna__.copy()
            label_value_map[grain.label] = new_value
        return self.model(**label_value_map)

    def to_dict(self, trunder_to_dash: bool=False) -> dict[str, Any]:
        """Returns a dictionary representation of the cob.

        Every sub-Barn is converted into a list of cobs,
        which are then converted to dictionaries recursively.
        Every sub-cob is converted to a dictionary too.

        Args:
            trunder_to_dash (bool): If True, converts triple
                underscores to hyphens in labels.

        Returns:
            A dictionary representation of the cob
        """
        # Lazy import to avoid circular imports
        from .barn import Barn
        from .cob import Cob
        label_value_map = {}
        for label, grain in self.label_grain_map.items():
            if trunder_to_dash: # Convert ___ to - in labels
                label = label.replace("___", "-")
            # If value is a barn or a cob, recursively process its cobs
            if isinstance(grain.value, Barn):
                barn = grain.value
                cobs = [cob.__dna__.to_dict(trunder_to_dash) for cob in barn]
                label_value_map[label] = cobs
            elif isinstance(grain.value, Cob):
                cob = grain.value
                label_value_map[label] = cob.__dna__.to_dict(trunder_to_dash)
            else:
                label_value_map[label] = grain.value
        return label_value_map
    
    def to_json(self, trunder_to_dash: bool=False, **json_kwargs) -> str:
        """Returns a JSON string representation of the cob.

        Every sub-Barn is converted into a list of cobs,
        which are then converted to dictionaries recursively.
        Every sub-cob is converted to a dictionary too.

        Args:
            trunder_to_dash (bool): If True, converts triple
                underscores to hyphens in labels.
            **json_kwargs: Additional keyword arguments to pass to json.dumps().

        Returns:
            A JSON string representation of the cob
        """
        import json # lazy import to avoid unecessary computation
        return json.dumps(self.to_dict(trunder_to_dash), **json_kwargs)