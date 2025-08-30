from typing import Any
from .dna import Dna
# Lazy import: typeguard

# GLOSSARY
# label = grain name
# value = grain value
# key = primary key value
# keyring = single key or tuple of composite keys


class CobMeta(type):
    """Sets the __dna__ attribute for the Cob-model."""

    def __new__(klass, name, bases, dikt):
        new_class = super().__new__(klass, name, bases, dikt)
        new_class.__dna__ = Dna(new_class)
        return new_class


class Cob(metaclass=CobMeta):
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
        # self.__dna__ = Dna(self.__class__, self)
        self.__dict__.update(__dna__=Dna(self.__class__, self))

        grains = list(self.__dna__.label_grain_map.values())

        for index, value in enumerate(args):
            grain = grains[index]
            setattr(self, grain.label, value)

        for label, value in kwargs.items():
            if self.__dna__.dynamic:
                self.__dna__._create_dynamic_grain(label)
            elif label not in self.__dna__.label_grain_map:
                raise NameError(f"Cannot assign '{label}={value}' because the grain"
                                f"'{label}' has not been defined in the cob-model. "
                                "Since at least one static grain has been defined in"
                                "the cob-model, dynamic grain assignment is not allowed.")
            setattr(self, label, value)

        for grain in grains:
            if not grain.was_set:
                setattr(self, grain.label, grain.default)

        if hasattr(self, "__post_init__"):
            self.__post_init__()

    def __setattr__(self, name: str, value: Any):
        if (grain := self.__dna__.label_grain_map.get(name)):
            if grain.type is not Any and value is not None:
                import typeguard  # Lazy import to avoid unecessary import
                try:
                    typeguard.check_type(value, grain.type)
                except typeguard.TypeCheckError:
                    raise TypeError(f"Cannot assign '{name}={value}' since the grain "
                                    f"was defined as {grain.type}, "
                                    f"but got {type(value)}.") from None
            if not grain.none and value is None and not grain.auto:
                raise ValueError(f"Cannot assign '{name}={value}' since the grain "
                                 "was defined as 'none=False'.")
            if grain.auto and (grain.was_set or (not grain.was_set and value is not None)):
                raise AttributeError(f"Cannot assign '{name}={value}' since the grain "
                                     "was defined as 'auto=True'.")
            if grain.frozen and grain.was_set:
                raise AttributeError(f"Cannot assign '{name}={value}' since the grain "
                                     "was defined as 'frozen=True'.")
            if grain.is_key and self.__dna__.barns:
                raise AttributeError(f"Cannot assign '{name}={value}' since the grain "
                                     "was defined as 'is_key=True' and the cob was appended to a barn.")
            if grain.unique and self.__dna__.barns:
                for barn in self.__dna__.barns:
                    barn._check_uniqueness_by_label(grain.label, value)
        super().__setattr__(name, value)
        if grain:
            grain.was_set = True
            self.__dna__._set_parent_if(grain)

    def __repr__(self) -> str:
        items = []
        for grain in self.__dna__.label_grain_map.values():
            items.append(f"{grain.label}={grain.value!r}")
        in_commas = ", ".join(items)
        return f"{type(self).__name__}({in_commas})"


def dict_to_cob(dikt: dict, dash_to_trunder: bool=False) -> Cob:
    """Recursively converts a dictionary to a Cob-like instance.

    If a value is a list of dictionaries, each dictionary is converted to
    a Cob-like instance and the list is converted to a Barn-like instance.
    
    Args:
        dikt (dict): The dictionary to convert.
        dash_to_trunder (bool): If True, replaces hyphens in keys with triple underscores.
    """
    if not isinstance(dikt, dict):
        raise TypeError(f"Expected a dictionary to convert to Cob, got {type(dikt)} instead.")
    new_dikt = dikt.copy()
    for key, value in dikt.items():
        if dash_to_trunder and "-" in key:
            key = key.replace("-", "___")  # Replace hyphens with triple underscores.
        if isinstance(value, dict):
            cob = dict_to_cob(value)
            new_dikt[key] = cob
        elif isinstance(value, list) and all(isinstance(item, dict) for item in value):
            # If the value is a list of dictionaries, convert each dict to a Cob.
            # Then, create a Barn instance to hold these Cobs.
            from .barn import Barn
            barn = Barn()
            for sub_value in value:
                cob = dict_to_cob(sub_value)
                barn.append(cob)
            new_dikt[key] = barn
    return Cob(**new_dikt)

def json_to_cob(json_str: str, dash_to_trunder: bool=False, **json_loads_kwargs) -> Cob:
    """Converts a JSON string to a Cob-like instance, through json.loads().

    If a value is a list of dictionaries, each dictionary is converted to
    a Cob-like instance and the list is converted to a Barn-like instance.

    Args:
        json_str (str): The JSON string to convert.
        dash_to_trunder (bool): If True, replaces hyphens in keys with triple underscores.
        **json_loads_kwargs: Additional keyword arguments to pass to json.loads().
    """
    import json
    dikt = json.loads(json_str, **json_loads_kwargs)
    return dict_to_cob(dikt, dash_to_trunder=dash_to_trunder)