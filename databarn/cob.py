from typing import Any
import copy
from .grain import Grain
from .trails import fo
from .dna import Dna
from .exceptions import ConsistencyError

# GLOSSARY
# label = grain var name in the cob
# key_name = grain key name in the dict/json output
# value = value dynamically getted from the cob attribute
# primakey = primary key value
# keyring = single primakey or tuple of composite primakeys


class MetaCob(type):
    """Sets the __dna__ attribute for the Cob-model."""

    def __new__(klass, name, bases, dikt):
        new_class = super().__new__(klass, name, bases, dikt)
        new_class.__dna__ = Dna(new_class)
        return new_class


class Cob(metaclass=MetaCob):
    """The base class for all in-memory data models."""

    def __init__(self, *args, **kwargs):
        """Initializes a Cob-like instance.

        - Positional args are assigned to the cob grains
        in the order they were declared in the Cob-model.
        - Static grain kwargs are assigned by name. If the grain is not
        defined in the cob-model, a NameError is raised.
        - Dynamic grain kwargs are assigned by name. You can do this if you
        didn't define any static grain in the cob-model.

        After all assignments, the `__post_init__` method is called, if defined.

        Args:
            *args: positional args to be assigned to grains
            **kwargs: keyword args to be assigned to grains
        """
        # Create a copy of the class's __dna__ to avoid modifying the class-level __dna__
        dna = copy.copy(self.__class__.__dna__)
        dna._set_cob_attrs(self)
        # Bypass __setattr__ by directly updating __dict__
        self.__dict__.update(__dna__=dna)

        grains = self.__dna__.grains

        for index, value in enumerate(args):
            grain = grains[index]
            setattr(self, grain.label, value)

        for label, value in kwargs.items():
            if self.__dna__.dynamic:
                self.__dna__._create_dynamic_grain(label)
            elif label not in self.__dna__.label_grain_map:
                raise ConsistencyError(fo(f"""
                        Cannot assign '{label}={value}' because the grain
                        '{label}' has not been defined in the Cob-model.
                        Since at least one static grain has been defined in
                        the Cob-model, dynamic grain assignment is not allowed."""))
            grain = self.__dna__.label_grain_map[label]
            if grain.wiz_child_model:
                raise ConsistencyError(fo(f"""
                    Cannot assign '{label}={value}' because the grain was
                    wiz created by wiz_create_child_barn."""))
            setattr(self, label, value)

        for grain in grains:
            value = grain.default
            if grain.wiz_child_model:
                # Avoid importing Barn at the top to avoid circular imports
                barn_class = grain.type # This should be Barn
                # Automatically create an empty Barn for the wiz_outer_model_grain
                value = barn_class(grain.wiz_child_model)
            if not grain.was_set:
                setattr(self, grain.label, value)
        if hasattr(self, "__post_init__"):
            self.__post_init__()

    def __setattr__(self, name: str, value: Any):
        """Sets the attribute value, with type and constraint checks.
        If the grain is not defined in the Cob-model, it is added as a dynamic grain.
        Args:
            name (str): The grain name.
            value (Any): The grain value.
        """
        grain = self.__dna__.label_grain_map.get(name, default=None)
        if grain:
            _check_and_set_up(self, grain, name, value)
        super().__setattr__(name, value)
        if grain:
            grain.was_set = True
            self.__dna__._set_parent_if(grain)

    def __repr__(self) -> str:
        items = []
        for grain in self.__dna__.grains:
            items.append(f"{grain.label}={grain.value!r}")
        in_commas = ", ".join(items)
        return f"{type(self).__name__}({in_commas})"


def _check_and_set_up(cob: Cob, grain: Grain, label: str, value: Any) -> None:
        if grain.type is not Any and value is not None:
            import typeguard  # Lazy import to avoid unecessary computation
            try:
                typeguard.check_type(value, grain.type)
            except typeguard.TypeCheckError:
                raise TypeError(f"Cannot assign '{label}={value}' since the grain "
                                f"was defined as {grain.type}, "
                                f"but got {type(value)}.") from None
        if not grain.none and value is None and not grain.auto:
            raise ValueError(f"Cannot assign '{label}={value}' since the grain "
                                "was defined as 'none=False'.")
        if grain.auto and (grain.was_set or (not grain.was_set and value is not None)):
            raise AttributeError(f"Cannot assign '{label}={value}' since the grain "
                                    "was defined as 'auto=True'.")
        if grain.frozen and grain.was_set:
            raise AttributeError(f"Cannot assign '{label}={value}' since the grain "
                                    "was defined as 'frozen=True'.")
        if grain.pk and cob.__dna__.barns:
            raise AttributeError(f"Cannot assign '{label}={value}' since the grain "
                                    "was defined as 'pk=True' and the cob has been added to a barn.")
        if grain.unique and cob.__dna__.barns:
            for barn in cob.__dna__.barns:
                barn._check_uniqueness_by_label(grain.label, value)
        if grain.was_set and grain.value is not value:
            cob.__dna__._remove_parent_if(grain)
        return None