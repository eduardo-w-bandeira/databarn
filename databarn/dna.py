from __future__ import annotations
import copy
from .exceptions import ConsistencyError
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
    grains: tuple # @property
    wiz_outer_model_grain: Grain | None = None  # Changed by the wiz_create_child_barn decorator

    # cob instance
    cob: "Cob" | None
    autoid: int | None # If the primakey is not provided, autoid will be used as primakey
    keyring: Any | tuple[Any]
    barns: set
    parent: "Cob" | None

    def __init__(self, model: Type["Cob"]):
        """Initializes the Meta object.

        Args:
            model: The Cob-like class.
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
        for value in list(self.model.__dict__.values()): # list() to avoid RuntimeError
            # issubclass() was not used because importing Cob would create a circular import
            if not hasattr(value, "__dna__"):
                continue
            child_model = value # Just to clarify
            # wiz_create_child_barn decorator previously had changed this attribute
            outer_model_grain = child_model.__dna__.wiz_outer_model_grain
            if outer_model_grain: # Wiz assign to the model
                setattr(self.model, outer_model_grain.label, outer_model_grain)
                annotations = get_type_hints(self.model)
                annotations[outer_model_grain.label] = outer_model_grain.type
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
        for grain in self.grains:
            new_grain = copy.copy(grain)
            new_grain._set_cob_attrs(cob=cob, was_set=False)
            new_label_grain_map[grain.label] = new_grain
        self.label_grain_map = new_label_grain_map
        self.barns = set()
        self.autoid = id(cob)  # Default autoid is the id of the cob instance
        self.parent = None

    def _set_up_parent_if(self, grain: Grain):
        # Lazy import to avoid circular imports
        from .barn import Barn
        from .cob import Cob
        if isinstance(grain.value, Barn):
            child_barn = grain.value
            child_barn._set_parent_cob(self.cob)
        elif isinstance(grain.value, Cob):
            child_cob = grain.value
            child_cob.__dna__.parent = self.cob

    def _remove_parent_if(self, grain: Grain):
        # Lazy import to avoid circular imports
        from .barn import Barn
        from .cob import Cob
        if isinstance(grain.value, Barn):
            child_barn = grain.value
            child_barn._remove_parent_cob()  # Remove the parent for the barn
        elif isinstance(grain.value, Cob):
            child_cob = grain.value
            child_cob.__dna__.parent = None
    
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
        """Returns a list of the cob's primakeys grains."""
        return tuple(self.label_grain_map[label] for label in self.primakey_labels)

    @property
    def keyring(self) -> Any | tuple[Any]:
        """Returns the keyring of the cob.

        The keyring is either a primakey or a tuple of primakeys. If the
        primakey-grain is not defined, the autoid is returned instead.

        Returns:
            tuple[Any] or Any: The keyring of the cob
        """
        if not self.primakey_defined:
            return self.autoid
        primakeys = tuple(grain.value for grain in self.primakey_grains)
        if not self.is_compos_primakey:
            return primakeys[0]
        return primakeys

    @property
    def grains(self) -> tuple[Grain]:
        """Returns a tuple of the cob's grains."""
        return tuple(self.label_grain_map.values())


    def to_dict(self) -> dict[Any, Any]:
        """Returns a dictionary representation of the cob.

        Every sub-Barn is converted into a list of cobs,
        which are then converted to dictionaries recursively.
        Every sub-cob is converted to a dictionary too.
        If key_name is set for a grain, it is used as the key instead of the label.

        Returns:
            A dictionary representation of the cob
        """
        # Lazy import to avoid circular imports
        from .barn import Barn
        from .cob import Cob
        key_value_map = {}
        for grain in self.grains:
            key_name = grain.key_name or grain.label
            # If value is a barn or a cob, recursively process its cobs
            if isinstance(grain.value, Barn):
                barn = grain.value
                cobs = [cob.__dna__.to_dict() for cob in barn]
                key_value_map[key_name] = cobs
            elif isinstance(grain.value, Cob):
                cob = grain.value
                key_value_map[key_name] = cob.__dna__.to_dict()
            else:
                key_value_map[key_name] = grain.value
        return key_value_map
    
    def to_json(self, **json_dumps_kwargs) -> str:
        """Returns a JSON string representation of the cob.

        Every sub-Barn is converted into a list of cobs,
        which are then converted to dictionaries recursively.
        Every sub-cob is converted to a dictionary too.

        Args:
            **json_dumps_kwargs:
                Additional keyword arguments to pass to json.dumps().

        Returns:
            A JSON string representation of the cob
        """
        import json # lazy import to avoid unecessary computation
        return json.dumps(self.to_dict(), **json_dumps_kwargs)

    def _check_and_set_up(self, grain: Grain, label: str, value: Any) -> None:
        """Checks the value against the grain constraints before setting it.

        Args:
            grain (Grain): The grain to check against.
            label (str): The grain label.
            value (Any): The value to check and set.
        Returns:
            None
        """
        if grain.type is not Any and value is not None:
            import typeguard  # Lazy import to avoid unecessary computation
            try:
                typeguard.check_type(value, grain.type)
            except typeguard.TypeCheckError:
                raise TypeError(f"Cannot assign '{label}={value}' because the grain "
                                f"was defined as {grain.type}, "
                                f"but got {type(value)}.") from None
        if grain.required and value is None and not grain.auto:
            raise ConsistencyError(f"Cannot assign '{label}={value}' because the grain "
                                "was defined as 'required=True'.")
        if grain.auto and (grain.was_set or (not grain.was_set and value is not None)):
            raise ConsistencyError(f"Cannot assign '{label}={value}' because the grain "
                                    "was defined as 'auto=True'.")
        if grain.frozen and grain.was_set:
            raise ConsistencyError(f"Cannot assign '{label}={value}' because the grain "
                                    "was defined as 'frozen=True'.")
        if grain.pk and self.barns:
            raise ConsistencyError(f"Cannot assign '{label}={value}' because the grain "
                                    "was defined as 'pk=True' and the cob has been added to a barn.")
        if grain.unique and self.barns:
            for barn in self.barns:
                barn._check_uniqueness_by_label(grain.label, value)
        if grain.was_set and grain.value is not value:
            # If the grain was previously set and the value is changing, remove parent links if any
            self._remove_parent_if(grain)
        return None