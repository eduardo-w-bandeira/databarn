from typing import Any
import re
from .trails import pascal_to_underscore, fo
from .exceptions import InvalidVarNameError
from .cob import Cob
from .barn import Barn
from .grain import Grain

def dict_to_cob(dikt: dict, replace_space_with: str | None = "_",
                replace_dash_with: str | None = "__") -> Cob:
    """Recursively converts a dictionary to a Cob-like instance.

    If a value is a list of dictionaries, each dictionary is converted to
    a Cob-like instance and the list is converted to a Barn-like instance.
    
    Args:
        dikt (dict): The dictionary to convert.
        replace_space_with (str | None): The string to replace spaces in keys with.
            If None, spaces are not replaced. Default is "_".
        replace_dash_with (str | None): The string to replace dashes in keys with.
            If None, dashes are not replaced. Default is "__" (dunder).
    """
    new_dikt = {}
    label_key_map = {}
    for key, value in dikt.items():
        if not isinstance(key, str):
            raise InvalidVarNameError(f"Key '{key}' is not a string.")
        label = key
        if replace_space_with is not None:
            label = label.replace(" ", replace_space_with)
        if replace_dash_with is not None:
            label = label.replace("-", replace_dash_with)
        if label in label_key_map:
            raise InvalidVarNameError(fo(f"""
                Key conflict after replacements: '{key}' and '{label_key_map[label]}'
                both map to '{label}'.
                """))
        if not label.isidentifier():
            raise InvalidVarNameError(f"Cannot convert key '{label}' to a valid variable name.")
        label_key_map[label] = key
        if isinstance(value, dict):
            new_dikt[label] = dict_to_cob(value, replace_space_with, replace_dash_with)
        elif isinstance(value, list) and all(isinstance(item, (dict, list)) for item in value):
            barn = Barn()
            for item in value:
                barn.add(dict_to_cob(item, replace_space_with, replace_dash_with))
            new_dikt[label] = barn
        else:
            new_dikt[label] = value
    cob = Cob(**new_dikt)
    for grain in cob.__dna__.grains:
        key_name = label_key_map[grain.label]
        grain._set_key_name(key_name)
    return cob
    

def json_to_cob(json_str: str, **json_loads_kwargs) -> Cob:
    """Converts a JSON string to a Cob-like instance, through json.loads().

    If a value is a list of dictionaries, each dictionary is converted to
    a Cob-like instance and the list is converted to a Barn-like instance.

    Args:
        json_str (str): The JSON string to convert.
        **json_loads_kwargs: Additional keyword arguments to pass to json.loads().
    """
    import json
    dikt = json.loads(json_str, **json_loads_kwargs)
    return dict_to_cob(dikt)


class _TempClass:
    """A temporary class used for type checking in wiz_create_child_barn."""
    pass

def wiz_create_child_barn(label: str="", default: Any = None, pk: bool = False,
                 auto: bool = False, none: bool = True, frozen: bool = False,
                 unique: bool = False, key_name: str="", **custom_attrs):
    """Decorator to define a Cob-like class as a sub-Barn grain in another Cob-like class.
    Args:
        label (str): The label of the grain. If not provided,
            it is generated from the class name in snake_case
            and pluralized by adding 's' if it doesn't already end with 's'.
        All other args: They are passed to the Grain constructor.
    Returns:
        A decorator that sets the Cob-like class as a sub-Barn grain.
    """
    grain = Grain(default=default, pk=pk, auto=auto, none=none, frozen=frozen,
                  unique=unique, key_name=key_name, **custom_attrs)
    # The decorator function that will be applied to the child Cob-like class
    def decorator(child_cob_model):
        if not issubclass(child_cob_model, Cob):
            raise TypeError("The decorated class must be a subclass of Cob.")
        nonlocal grain, label
        if not label:
            label = pascal_to_underscore(child_cob_model.__name__)
            label += "s" if not label.endswith("s") else ""
        grain._set_model_attrs(model=_TempClass, label=label, type=Barn)
        grain._set_wiz_child_model(child_cob_model)
        child_cob_model.__dna__.wiz_outer_model_grain = grain
        return child_cob_model
    return decorator