from typing import Callable, Any
import keyword
from .trails import fo
from .exceptions import InvalidGrainLabelError, DataBarnSyntaxError
from .cob import Cob
from .barn import Barn
from .grain import Grain

_ref_cob = Cob()


def _key_to_label(key: Any,
                  replace_space_with: str,
                  replace_dash_with: str,
                  suffix_keyword_with: str,
                  prefix_leading_num_with: str,
                  replace_invalid_char_with: str,
                  suffix_existing_attr_with: str,
                  custom_key_converter: Callable) -> str:
    if custom_key_converter is not None:
        label: Any = custom_key_converter(key)
        if type(label) is not str:
            raise DataBarnSyntaxError(fo(f"""
                Custom key converter must return a string, got {type(label)} instead."""))
        return label
    label: str = str(key)  # Ensure it's a string
    if suffix_keyword_with is not None and keyword.iskeyword(label):
        label += suffix_keyword_with
        return label
    if replace_space_with is not None:
        label = label.replace(" ", replace_space_with)
    if replace_dash_with is not None:
        label = label.replace("-", replace_dash_with)
    if prefix_leading_num_with is not None and label and label[0].isdigit():
        label = prefix_leading_num_with + label
    if replace_invalid_char_with is not None:
        chars = []
        for char in label:
            if not char.isalnum() and char != '_':
                char = replace_invalid_char_with
            chars.append(char)
        label = ''.join(chars)
    if suffix_existing_attr_with is not None and hasattr(_ref_cob, label):
        label += suffix_existing_attr_with
    return label

def verify_label(label: str, key: str, label_key_map: dict):
    if hasattr(_ref_cob, label):
        raise InvalidGrainLabelError(
            f"Key '{key}' maps to a Cob attribute '{label}'.")
    if label in label_key_map:
        raise InvalidGrainLabelError(fo(f"""
            Key conflict after replacements: '{key}' and '{label_key_map[label]}'
            both map to '{label}'.
            """))
    if not label.isidentifier():
        raise InvalidGrainLabelError(fo(f"""
            Cannot convert key '{key}' to a valid var name: '{label}'"""))
    return True

def _convert_sub_dict_if(model, label, value,
                         replace_space_with, replace_dash_with,
                         suffix_keyword_with, prefix_leading_num_with,
                         replace_invalid_char_with, suffix_existing_attr_with,
                         custom_key_converter):
    class Converted(Cob):
        new_value: Any = Grain()
        is_child_barn: bool = Grain(default=False)

    child_model: type[Cob] = Cob
    if isinstance(value, dict):
        if not model.__dna__.dynamic:
            grain = model.__dna__.get_grain(label)
            if issubclass(grain.type, dict):
                # If the grain type is dict, keep it as dict.
                # Eventual sub-dicts won't be converted to Cob
                return Converted(value)
            if grain.child_model:
                child_model = grain.child_model
        cob = dict_to_cob(
            dikt=value,
            model=child_model,
            replace_space_with=replace_space_with,
            replace_dash_with=replace_dash_with,
            suffix_keyword_with=suffix_keyword_with,
            prefix_leading_num_with=prefix_leading_num_with,
            replace_invalid_char_with=replace_invalid_char_with,
            suffix_existing_attr_with=suffix_existing_attr_with,
            custom_key_converter=custom_key_converter)
        return Converted(cob)
    if isinstance(value, list):
        cobs_or_miscs: list = []
        if not model.__dna__.dynamic:
            grain = model.__dna__.get_grain(label)
            if grain.child_model:
                child_model = grain.child_model
        for item in value:
            new_item: Any = item
            if isinstance(item, dict):
                new_item: Cob = dict_to_cob(
                    dikt=item,
                    model=child_model,
                    replace_space_with=replace_space_with,
                    replace_dash_with=replace_dash_with,
                    suffix_keyword_with=suffix_keyword_with,
                    prefix_leading_num_with=prefix_leading_num_with,
                    replace_invalid_char_with=replace_invalid_char_with,
                    suffix_existing_attr_with=suffix_existing_attr_with,
                    custom_key_converter=custom_key_converter)
            cobs_or_miscs.append(new_item)
        only_cobs: bool = cobs_or_miscs and all(
            isinstance(i, Cob) for i in cobs_or_miscs)
        if not model.__dna__.dynamic:
            if grain.is_child_barn_ref:
                # This will be added to the child barn after final cob is created
                return Converted(cobs_or_miscs, is_child_barn=True)
            if (only_cobs and not issubclass(grain.type, list)) or \
                    (not cobs_or_miscs and issubclass(grain.type, Barn)):
                child_barn = Barn(child_model)
                [child_barn.add(cob) for cob in cobs_or_miscs]
                return Converted(child_barn)
            return Converted(cobs_or_miscs)
        if only_cobs:
            child_barn = Barn(child_model)
            [child_barn.add(cob) for cob in cobs_or_miscs]
            return Converted(child_barn)
        return Converted(cobs_or_miscs)
    return Converted(value)


def dict_to_cob(dikt: dict,
                model: type[Cob] = Cob,
                replace_space_with: str | None = "_",
                replace_dash_with: str | None = "__",
                suffix_keyword_with: str | None = "_",
                prefix_leading_num_with: str | None = "n_",
                replace_invalid_char_with: str | None = "_",
                suffix_existing_attr_with: str | None = "_",
                custom_key_converter: Callable | None = None) -> Cob:
    """Recursively converts a dictionary to a Cob-like object.

    If a value is a list of dictionaries, each dictionary is converted to
    a Cob-like object and the list is converted to a Barn-like object.
    Every converted key is stored in the correspoding cob.__dna__.get_grain(label).key.
    So that when the cob is converted back to a dict, the original keys are preserved.

    All keys are converted to string and to a valid Python variable name, following these rules:
    - Spaces can be replaced with a specified string (default is "_").
    - Dashes can be replaced with a specified string (default is "__" (dunder)).
    - If a key is a Python keyword, a specified string can be appended (default is "_").
    - If a key starts with a number, a specified string can be prepended (default is "n_").
    - Non-alphanumeric (and not underscore) chars can be replaced with a specified string
        (default is "_").
    - If a key conflicts with an existing Cob attribute, a specified string can be appended
        (default is "_").
    - A custom key conversion function can be provided to override the above rules.
    - If after all replacements, a key is still not a valid identifier, an InvalidGrainLabelError is raised.
    - If after all replacements, two keys conflict, an InvalidGrainLabelError is raised.

    Args:
        dikt (dict): The dictionary to convert.
        model (type[Cob]): The Cob-like class to instantiate. Default is Cob.
        replace_space_with (str | None): The string to replace spaces in keys with.
            If None, spaces are not replaced. Default is "_".
        replace_dash_with (str | None): The string to replace dashes in keys with.
            If None, dashes are not replaced. Default is "__" (dunder).
        suffix_keyword_with (str | None): The string to append to keys that are
            Python keywords. If None, keywords are not modified. Default is "_".
        prefix_leading_num_with (str | None): The string to prepend to keys that
            start with a number. If None, leading numbers are not modified.
            Default is "n_".
        replace_invalid_char_with (str | None): The string to replace invalid
            characters in keys with. If None, invalid characters are not replaced.
            Default is "_".
        suffix_existing_attr_with (str | None): The string to append to keys that
            conflict with existing Cob attributes. If None, existing attributes
            are not modified. Default is "_".
        custom_key_converter (Callable | None): A custom function that takes a key
            and returns a modified string key. If provided, this function is used instead
            of the above replacement rules.

    Returns:
        Cob: The converted Cob-like object."""
    if not isinstance(dikt, dict):
        raise TypeError("'dikt' must be a dictionary.")
    label_value_map = {}
    label_child_cobs_map = {}
    label_key_map = {}
    for key, value in dikt.items():
        label: str = _key_to_label(key=key,
                                   replace_space_with=replace_space_with,
                                   replace_dash_with=replace_dash_with,
                                   suffix_keyword_with=suffix_keyword_with,
                                   prefix_leading_num_with=prefix_leading_num_with,
                                   replace_invalid_char_with=replace_invalid_char_with,
                                   suffix_existing_attr_with=suffix_existing_attr_with,
                                   custom_key_converter=custom_key_converter,)
        verify_label(label, key, label_key_map)
        label_key_map[label] = key

        converted = _convert_sub_dict_if(model=model, label=label, value=value,
                                         replace_space_with=replace_space_with,
                                         replace_dash_with=replace_dash_with,
                                         suffix_keyword_with=suffix_keyword_with,
                                         prefix_leading_num_with=prefix_leading_num_with,
                                         replace_invalid_char_with=replace_invalid_char_with,
                                         suffix_existing_attr_with=suffix_existing_attr_with,
                                         custom_key_converter=custom_key_converter)
        right_dict: dict = label_value_map
        if converted.is_child_barn:
            right_dict = label_child_cobs_map
        right_dict[label] = converted.new_value

    cob = model(**label_value_map)
    for grain in cob.__dna__.grains:
        key = label_key_map[grain.label]
        grain.set_key(key)
    for label, child_cobs in label_child_cobs_map.items():
        seed = cob.__dna__.get_seed(label)
        child_barn = seed.get_value()
        [child_barn.add(child_cob) for child_cob in child_cobs]
    return cob


def json_to_cob(json_str: str,
                model: type[Cob] = Cob,
                replace_space_with: str | None = "_",
                replace_dash_with: str | None = "__",
                suffix_keyword_with: str | None = "_",
                prefix_leading_num_with: str | None = "n_",
                replace_invalid_char_with: str | None = "_",
                suffix_existing_attr_with: str | None = "_",
                custom_key_converter: Callable | None = None,
                **json_loads_kwargs) -> Cob:
    """Converts a JSON string to a Cob-like object, through json.loads().

    If a value is a list of dictionaries, each dictionary is converted to
    a Cob-like object and the list is converted to a Barn-like object.

    Args:
        json_str (str): The JSON string to convert.
        model (type[Cob]): The Cob-like class to instantiate. Default is Cob.
        replace_space_with (str | None): See dict_to_cob() for reference.
        replace_dash_with (str | None): See dict_to_cob() for reference.
        suffix_keyword_with (str | None): See dict_to_cob() for reference.
        prefix_leading_num_with (str | None): See dict_to_cob() for reference
        replace_invalid_char_with (str | None): See dict_to_cob() for reference.
        suffix_existing_attr_with (str | None): See dict_to_cob() for reference.
        custom_key_converter (Callable | None): See dict_to_cob() for reference.        
        **json_loads_kwargs: Additional keyword arguments to pass to json.loads().

    Returns:
        Cob: The converted Cob-like object.
    """
    import json
    dikt = json.loads(json_str, **json_loads_kwargs)
    return dict_to_cob(dikt=dikt,
                       model=model,
                       replace_space_with=replace_space_with,
                       replace_dash_with=replace_dash_with,
                       suffix_keyword_with=suffix_keyword_with,
                       prefix_leading_num_with=prefix_leading_num_with,
                       replace_invalid_char_with=replace_invalid_char_with,
                       suffix_existing_attr_with=suffix_existing_attr_with,
                       custom_key_converter=custom_key_converter)
