from typing import Callable
import keyword
from .trails import fo
from .exceptions import InvalidGrainLabelError
from .cob import Cob
from .barn import Barn

def dict_to_cob(dikt: dict, replace_space_with: str | None = "_",
                replace_dash_with: str | None = "__",
                add_keyword_suffix: str | None = "_",
                add_existing_attr_suffix: str | None = "_",
                custom_key_converter: Callable | None = None) -> Cob:
    """Recursively converts a dictionary to a Cob-like object.

    If a value is a list of dictionaries, each dictionary is converted to
    a Cob-like object and the list is converted to a Barn-like object.
    Every converted key is stored in the correspoding cob.__dna__.seeds[n].key_name.
    So that when the cob is converted back to a dict, the original keys are preserved.

    Args:
        dikt (dict): The dictionary to convert.
        replace_space_with (str | None): The string to replace spaces in keys with.
            If None, spaces are not replaced. Default is "_".
        replace_dash_with (str | None): The string to replace dashes in keys with.
            If None, dashes are not replaced. Default is "__" (dunder).
        add_keyword_suffix (str | None): The string to append to keys that are Python keywords.
            If None, keywords are not modified. Default is "_".
        add_existing_attr_suffix (str | None): The string to append to keys that
            conflict with existing Cob attributes (like '__dna__', '__setattr__', etc).
            If None, existing attributes are not modified. Default is "_".
        custom_key_converter (Callable | None): A custom function to convert keys.
            It takes the original key and returns a converted string.
            If provided, it is applied before other replacements.

    Returns:
        Cob: The converted Cob-like object."""
    if not isinstance(dikt, dict):
        # Recursively secure against non-dict inputs
        raise TypeError("'dikt' must be a dictionary.")
    new_dikt = {}
    label_key_map = {}
    for key, value in dikt.items():
        if not isinstance(key, str):
            raise InvalidGrainLabelError(f"Key '{key}' is not a string.")
        label = key
        if custom_key_converter is not None:
            label = custom_key_converter(label)
        if keyword.iskeyword(label) and add_keyword_suffix is not None:
            label += add_keyword_suffix
        if replace_space_with is not None:
            label = label.replace(" ", replace_space_with)
        if replace_dash_with is not None:
            label = label.replace("-", replace_dash_with)
        if add_existing_attr_suffix is not None:
            while hasattr(Cob, label):
                label += add_existing_attr_suffix
        if label in label_key_map:
            raise InvalidGrainLabelError(fo(f"""
                Key conflict after replacements: '{key}' and '{label_key_map[label]}'
                both map to '{label}'.
                """))
        if not label.isidentifier():
            raise InvalidGrainLabelError(
                f"Cannot convert key '{label}' to a valid var name.")
        label_key_map[label] = key
        if isinstance(value, dict):
            cob = dict_to_cob(
                dikt=value, replace_space_with=replace_dash_with,
                replace_dash_with=replace_dash_with,
                add_keyword_suffix=add_keyword_suffix,
                add_existing_attr_suffix=add_existing_attr_suffix,
                custom_key_converter=custom_key_converter)
            new_dikt[label] = cob
        elif isinstance(value, list):
            collection: list | Barn = []
            if value and all(isinstance(item, dict) for item in value):
                collection = Barn()
            for item in value:
                new_item = item
                if isinstance(item, dict):
                    new_item = dict_to_cob(
                        dikt=item, replace_space_with=replace_dash_with,
                        replace_dash_with=replace_dash_with,
                        add_keyword_suffix=add_keyword_suffix,
                        add_existing_attr_suffix=add_existing_attr_suffix,
                        custom_key_converter=custom_key_converter)
                collection.append(new_item)  # Either Barn or list
            new_dikt[label] = collection
        else:
            new_dikt[label] = value
    cob = Cob(**new_dikt)
    for grain in cob.__dna__.grains:
        key_name = label_key_map[grain.label]
        grain.set_key_name(key_name)
    return cob


def json_to_cob(json_str: str, replace_space_with: str | None = "_",
                replace_dash_with: str | None = "__",
                add_keyword_suffix: str | None = "_",
                add_existing_attr_suffix: str | None = "_",
                custom_key_converter: Callable | None = None,
                **json_loads_kwargs) -> Cob:
    """Converts a JSON string to a Cob-like object, through json.loads().

    If a value is a list of dictionaries, each dictionary is converted to
    a Cob-like object and the list is converted to a Barn-like object.

    Args:
        json_str (str): The JSON string to convert.
        replace_space_with (str | None): See dict_to_cob() for reference.
        replace_dash_with (str | None): See dict_to_cob() for reference.
        add_keyword_suffix (str | None): See dict_to_cob() for reference.
        custom_key_converter (Callable): See dict_to_cob() for reference.
        **json_loads_kwargs: Additional keyword arguments to pass to json.loads().

    Returns:
        Cob: The converted Cob-like object.
    """
    import json
    dikt = json.loads(json_str, **json_loads_kwargs)
    return dict_to_cob(dikt=dikt, replace_space_with=replace_space_with,
                       replace_dash_with=replace_dash_with,
                       add_keyword_suffix=add_keyword_suffix,
                       add_existing_attr_suffix=add_existing_attr_suffix,
                       custom_key_converter=custom_key_converter)
