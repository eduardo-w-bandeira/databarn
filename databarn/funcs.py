import re
from .exceptions import InvalidVarNameError
from .cob import Cob
from .barn import Barn
from .grain import Grain

def dict_to_cob(dikt: dict, dash_to_trunder: bool=False) -> Cob:
    """Recursively converts a dictionary to a Cob-like instance.

    If a value is a list of dictionaries, each dictionary is converted to
    a Cob-like instance and the list is converted to a Barn-like instance.
    
    Args:
        dikt (dict): The dictionary to convert.
        dash_to_trunder (bool): If True, replaces hyphens in keys with triple underscores.
    """
    new_dikt = {}
    for key, value in dikt.items():
        if dash_to_trunder:
            key = key.replace("-", "___")
        if not isinstance(key, str) or not key.isidentifier():
            raise InvalidVarNameError(f"Cannot convert key '{key}' to a valid variable name.")
        if isinstance(value, dict):
            new_dikt[key] = dict_to_cob(value, dash_to_trunder=dash_to_trunder)
        elif isinstance(value, list) and all(isinstance(item, (dict, list)) for item in value):
            barn = Barn()
            for item in value:
                barn.append(dict_to_cob(item, dash_to_trunder=dash_to_trunder))
            new_dikt[key] = barn
        else:
            new_dikt[key] = value
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


def pascal_to_underscore(name: str) -> str:
    """Converts a PascalCase name to underscore_case.
    Args:
        name (str): The PascalCase name to convert.
    Returns:
        str: The converted underscore_case name.
    """
    # Insert underscore before each capital letter (except the first one)
    # and convert the entire string to lowercase
    underscore = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    return underscore

class _TempClass:
    """A temporary class used for type checking in wiz_build_child_barn."""
    pass

def wiz_build_child_barn(label: str="", **grain_kwargs):
    """Decorator to define a Cob-like class as a sub-Barn grain in another Cob-like class.
    Args:
        label (str): The label of the grain. If not provided,
            it is generated from the class name in snake_case
            and pluralized by adding 's' if it doesn't already end with 's'.
        **grain_kwargs: Additional keyword arguments to pass to the Grain constructor.
    Returns:
        A decorator that sets the Cob-like class as a sub-Barn grain.
    """
    def decorator(child_cob_model):
        nonlocal label, grain_kwargs
        grain = Grain(**grain_kwargs)
        if not label:
            label = pascal_to_underscore(child_cob_model.__name__)
            label += "s" if not label.endswith("s") else ""
        grain._set_model_attrs(bound_model=_TempClass, label=label, type=Barn)
        grain._set_wiz_child_model(child_cob_model)
        child_cob_model.__dna__.wiz_outer_model_grain = grain
        return child_cob_model
    return decorator