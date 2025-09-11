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
        self.__dict__.update(__dna__=dna) # Bypass __setattr__

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
                    created by wiz_create_child_barn."""))
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
        """Sets the attribute value, with type and constraint checks for the grain.
        
        Args:
            name (str): The grain name.
            value (Any): The grain value.
        """
        grain = self.__dna__.label_grain_map.get(name, default=None)
        if grain:
            self.__dna__._check_and_set_up(grain, name, value)
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


