from typing import Callable, Any
import keyword
from .trails import fo
from .exceptions import DataBarnViolationError, InvalidGrainLabelError, DataBarnSyntaxError
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


def verify_label(label: str, key: str, label_key_map: dict) -> None:
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


def _process_dict_if(value: Any, model: type[Cob], label: str,
                     replace_space_with: str | None,
                     replace_dash_with: str | None,
                     suffix_keyword_with: str | None,
                     prefix_leading_num_with: str | None,
                     replace_invalid_char_with: str | None,
                     suffix_existing_attr_with: str | None,
                     custom_key_converter: Callable | None) -> Cob:
    class Outcome(Cob):
        new_value: Any = Grain()
        is_child_barn_ref: bool = Grain(default=False)

    child_model: type[Cob] = Cob
    grain: Grain | None = model.__dna__.get_grain(label, default=None)
    if isinstance(value, dict):
        # If grain was defined (static model), respect grain type
        if grain and issubclass(grain.type, dict):
            # Eventual sub-dicts won't be converted to Cob
            return Outcome(value)
        # If grain has child model, use it
        if grain and grain.child_model:
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
        return Outcome(cob)
    if isinstance(value, list):
        cobs_or_miscs: list = []
        if grain and grain.child_model:
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
        only_cobs: bool = all(isinstance(i, Cob) for i in cobs_or_miscs)
        if grain:
            if not only_cobs and (grain.is_child_barn_ref or issubclass(grain.type, Barn)):
                raise DataBarnViolationError(fo(f"""
                    Grain '{label}' expects a Barn of Cobs,
                    but found non-Cob item in the list
                    (Item: {item}. List: {value})."""))
            # If Grain was created by a decorator as a child barn ref,
            # keep as list for now, to be added to child barn later
            if grain.is_child_barn_ref:
                # This will be added to the child barn after final cob is created
                return Outcome(cobs_or_miscs, is_child_barn=True)
            if issubclass(grain.type, Barn):
                child_barn = child_model.__dna__.create_barn()
                [child_barn.add(cob) for cob in cobs_or_miscs]
                return Outcome(child_barn)
            # Otherwise, keep as list
            return Outcome(cobs_or_miscs)
        # If no grain was defined, but all items are Cobs, create a child barn
        if only_cobs and cobs_or_miscs:
            child_barn = child_model.__dna__.create_barn()
            [child_barn.add(cob) for cob in cobs_or_miscs]
            return Outcome(child_barn)
        # If no grain was defined or mixed items, keep as list
        return Outcome(cobs_or_miscs)
    # If not dict or list, keep as it is
    return Outcome(value)


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

        outcome = _process_dict_if(value=value, model=model, label=label,
                                   replace_space_with=replace_space_with,
                                   replace_dash_with=replace_dash_with,
                                   suffix_keyword_with=suffix_keyword_with,
                                   prefix_leading_num_with=prefix_leading_num_with,
                                   replace_invalid_char_with=replace_invalid_char_with,
                                   suffix_existing_attr_with=suffix_existing_attr_with,
                                   custom_key_converter=custom_key_converter)
        target_dict: dict = label_value_map
        if outcome.is_child_barn_ref:
            target_dict = label_child_cobs_map
        target_dict[label] = outcome.new_value

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
