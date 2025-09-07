from __future__ import annotations
import copy
import inspect
from .grain import Grain
from typing import Any, Type, get_type_hints

class Dna:

    # Model
    label_grain_map: dict
    primakey_labels: list[str]
    primakey_grains: tuple[Grain] # @property
    is_compos_primakey: bool
    primakey_defined: bool
    keyring_len: int
    dynamic: bool
    grains: list # @property
    wiz_outer_model_grain: Grain | None = None  # Changed by the wiz_create_child_barn decorator

    # cob instance
    cob: "Cob" | None
    autoid: int | None # If the key is not provided, autoid will be used as key
    keyring: Any | tuple[Any]
    barns: set
    parent: "Cob" | None

    def __init__(self, model: Type["Cob"]):
        """Initializes the Meta object.

        Args:
            model: The Cob-like class.
            cob: The cob instance. If provided, it assumes this object is for a cob instance.
        """
        self.model = model
        self.primakey_labels = []
        self.label_grain_map = {} # A new dict is created for every cob instance
        self._assign_wiz_child_grain()
        for name, value in list(model.__dict__.items()):  # list() to avoid RuntimeError
            if not isinstance(value, Grain):
                continue
            self._set_up_grain(value, name)
        self.dynamic = False if self.label_grain_map else True
        self.primakey_defined = len(self.primakey_grains) > 0
        self.is_compos_primakey = len(self.primakey_grains) > 1
        self.keyring_len = len(self.primakey_grains) or 1

    def _assign_wiz_child_grain(self) -> None:
        # Avoid importing Cob here, since it causes circular imports
        cob_class = self.model.__mro__[-2] # The Cob class is always the second last in the MRO
        for value in list(self.model.__dict__.values()): # list() to avoid RuntimeError
            if inspect.isclass(value) and issubclass(value, cob_class) and hasattr(value, "__dna__"): # A Cob-like class
                child_model = value # Just to clarify
                # wiz_create_child_barn decorator previously had changed this attribute
                wiz_grain = child_model.__dna__.wiz_outer_model_grain
                if wiz_grain: # Wiz assign to the model
                    setattr(self.model, wiz_grain.label, wiz_grain)
                    annotations = get_type_hints(self.model)
                    annotations[wiz_grain.label] = wiz_grain.type
                    self.model.__annotations__ = annotations

    def _set_up_grain(self, grain: Grain, label: str) -> None:
        type_ = Any
        if label in self.model.__annotations__:
            type_ = self.model.__annotations__[label]
        grain._set_model_attrs(model=self.model, label=label, type=type_)
        if grain.pk:
            self.primakey_labels.append(grain.label)
        self.label_grain_map[label] = grain

    def _set_cob_attrs(self, cob: "Cob") -> None:
        self.cob = cob
        new_label_grain_map = {}
        for label, grain in self.label_grain_map.items():
            new_grain = copy.copy(grain)
            new_grain._set_cob_attrs(cob=cob, was_set=False)
            new_label_grain_map[label] = new_grain
        self.label_grain_map = new_label_grain_map
        self.barns = set()
        self.autoid = None
        self.parent = None

    def _set_parent_if(self, grain: Grain):
        # Lazy import to avoid circular imports
        from .barn import Barn
        from .cob import Cob
        if isinstance(grain.value, Barn):
            barn = grain.value
            barn._set_parent_cob(self.cob)  # Set the parent for the barn
        elif isinstance(grain.value, Cob):
            grain.value.__dna__.parent = self.cob

    def _create_dynamic_grain(self, label: str) -> Grain:
        """Adds a dynamic grain to the Meta object.

        Args:
            label: The label of the dynamic grain to add

        This method is private solely to hide it from the user,
        but it will be called by the cob when a dynamic grain is created.
        """
        grain = Grain()
        self._set_up_grain(grain, label)
        grain._set_cob_attrs(cob=self.cob, was_set=False)


    def create_barn(self):
        from .barn import Barn # Lazy import to avoid circular imports
        return Barn(self.model)

    @property
    def primakey_grains(self) -> tuple[Grain]:
        """Returns a list of the cob's primary key grains."""
        return tuple(self.label_grain_map[label] for label in self.primakey_labels)

    @property
    def keyring(self) -> Any | tuple[Any]:
        """Returns the keyring of the cob.

        The keyring is either a key or a tuple of keys. If the
        key-grain is not defined, the autoid is returned instead.

        Returns:
            tuple[Any] or Any: The keyring of the cob
        """
        if not self.primakey_defined:
            return self.autoid
        keys = tuple(grain.value for grain in self.primakey_grains)
        if not self.is_compos_primakey:
            return keys[0]
        return keys

    @property
    def grains(self) -> list[Grain]:
        """Returns a list of the cob's grains."""
        return list(self.label_grain_map.values())


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