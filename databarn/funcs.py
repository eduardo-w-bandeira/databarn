from collections.abc import Callable, Mapping
from typing import Any
import keyword
from .trails import fo
from .exceptions import GrainLabelError, DataBarnSyntaxError, BarnConstraintViolationError
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
                  custom_key_converter: Callable[[Any], str] | None) -> str:
    """Convert an input dictionary key into a candidate Grain label.

    Args:
        key: Original key from source dictionary/JSON.
        replace_space_with: Replacement for spaces.
        replace_dash_with: Replacement for dashes.
        suffix_keyword_with: Suffix for Python keyword labels.
        prefix_leading_num_with: Prefix for labels that start with digits.
        replace_invalid_char_with: Replacement for non-identifier characters.
        suffix_existing_attr_with: Suffix for labels colliding with Cob attributes.
        custom_key_converter: Optional converter that overrides built-in rules.

    Returns:
        A normalized label candidate.
    """
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


def _verify_label(label: str, key: str, label_key_map: dict[str, Any]) -> None:
    """Validate a generated label and guard against conflicts.

    Args:
        label: Candidate label to validate.
        key: Original source key used to create ``label``.
        label_key_map: Mapping of labels already claimed by earlier keys.
    """
    if hasattr(_ref_cob, label):
        raise GrainLabelError(
            f"Key '{key}' maps to a Cob attribute '{label}'.")
    if label in label_key_map:
        raise GrainLabelError(fo(f"""
            Key conflict after replacements: '{key}' and '{label_key_map[label]}'
            both map to '{label}'.
            """))
    if not label.isidentifier():
        raise GrainLabelError(fo(f"""
            Cannot convert key '{key}' to a valid var name: '{label}'"""))


def _process_dict_if(value: Any, model: type[Cob], label: str,
                     replace_space_with: str | None,
                     replace_dash_with: str | None,
                     suffix_keyword_with: str | None,
                     prefix_leading_num_with: str | None,
                     replace_invalid_char_with: str | None,
                     suffix_existing_attr_with: str | None,
                     custom_key_converter: Callable[[Any], str] | None) -> Cob:
    """Convert nested dict/list values into Cob/Barn structures when appropriate.

    Args:
        value: Raw value from the source dictionary.
        model: Target Cob model currently being constructed.
        label: Grain label associated with ``value``.
        replace_space_with: See :func:`dict_to_cob`.
        replace_dash_with: See :func:`dict_to_cob`.
        suffix_keyword_with: See :func:`dict_to_cob`.
        prefix_leading_num_with: See :func:`dict_to_cob`.
        replace_invalid_char_with: See :func:`dict_to_cob`.
        suffix_existing_attr_with: See :func:`dict_to_cob`.
        custom_key_converter: See :func:`dict_to_cob`.

    Returns:
        An ``Outcome`` cob with ``new_value`` and ``is_child_barn`` metadata.
    """
    class Outcome(Cob):
        new_value: Any = Grain(required=True)
        is_child_barn: bool = False

    child_model = Cob # Dynamic model by default
    grain: Grain | None = model.__dna__.get_grain(label, default=None)
    # If grain is defined, it's a static model
    if grain and grain.child_model:
        child_model = grain.child_model
    
    if isinstance(value, dict):
        # If grain has no child model or type is dict, keep as dict
        if grain and not grain.child_model:
            # Eventual sub-dicts won't be converted to Cob
            return Outcome(new_value=value)
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
        return Outcome(new_value=cob)
    if isinstance(value, list):
        cobs_or_miscs: list = []
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
            if not only_cobs and (grain.is_child_barn or issubclass(grain.type, Barn)):
                raise BarnConstraintViolationError(fo(f"""
                    Grain '{label}' expects a Barn of Cobs,
                    but found non-Cob item in the list
                    (Item: {item}. List: {value})."""))
            # If Grain was created by a decorator as a child barn ref,
            # keep as list for now, to be added to child barn later
            if grain.is_child_barn:
                # This will be added to the child barn after final cob is created
                return Outcome(new_value=cobs_or_miscs, is_child_barn=True)
            if issubclass(grain.type, Barn):
                child_barn = child_model.__dna__.create_barn()
                [child_barn.add(cob) for cob in cobs_or_miscs]
                return Outcome(new_value=child_barn)
            # Otherwise, keep as list
            return Outcome(new_value=cobs_or_miscs)
        # If no grain was defined, but all items are Cobs, create a child barn
        if only_cobs and cobs_or_miscs:
            child_barn = child_model.__dna__.create_barn()
            [child_barn.add(cob) for cob in cobs_or_miscs]
            return Outcome(new_value=child_barn)
        # If no grain was defined or mixed items, keep as list
        return Outcome(new_value=cobs_or_miscs)
    # If not dict or list, keep as it is
    return Outcome(new_value=value)

def dict_to_cob(dikt: dict[str, Any],
                model: type[Cob] = Cob,
                replace_space_with: str | None = "_",
                replace_dash_with: str | None = "__",
                suffix_keyword_with: str | None = "_",
                prefix_leading_num_with: str | None = "n_",
                replace_invalid_char_with: str | None = "_",
                suffix_existing_attr_with: str | None = "_",
                custom_key_converter: Callable[[Any], str] | None = None) -> Cob:
    """Recursively convert a dictionary into a Cob instance.

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
    - If after all replacements, a key is still not a valid identifier, an GrainLabelError is raised.
    - If after all replacements, two keys conflict, an GrainLabelError is raised.

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
        Cob: The converted Cob object.
    """
    if not isinstance(dikt, dict):
        raise TypeError("'dikt' must be a dictionary.")
    label_value_map: dict[str, Any] = {}
    label_child_cobs_map: dict[str, list[Cob]] = {}
    label_key_map: dict[str, Any] = {}
    for key, value in dikt.items():
        label: str = _key_to_label(key=key,
                                   replace_space_with=replace_space_with,
                                   replace_dash_with=replace_dash_with,
                                   suffix_keyword_with=suffix_keyword_with,
                                   prefix_leading_num_with=prefix_leading_num_with,
                                   replace_invalid_char_with=replace_invalid_char_with,
                                   suffix_existing_attr_with=suffix_existing_attr_with,
                                   custom_key_converter=custom_key_converter,)
        _verify_label(label, key, label_key_map)
        label_key_map[label] = key

        outcome = _process_dict_if(value=value, model=model, label=label,
                                   replace_space_with=replace_space_with,
                                   replace_dash_with=replace_dash_with,
                                   suffix_keyword_with=suffix_keyword_with,
                                   prefix_leading_num_with=prefix_leading_num_with,
                                   replace_invalid_char_with=replace_invalid_char_with,
                                   suffix_existing_attr_with=suffix_existing_attr_with,
                                   custom_key_converter=custom_key_converter)
        target_dict: dict[str, Any] = label_value_map
        if outcome.is_child_barn:
            target_dict = label_child_cobs_map
        target_dict[label] = outcome.new_value

    cob = model(**label_value_map)
    for grain in cob.__dna__.grains:
        if grain.label in label_key_map:
            key = label_key_map[grain.label]
            grain.set_key(key)
    for label, child_cobs in label_child_cobs_map.items():
        grist = cob.__dna__.get_grist(label)
        child_barn = grist.get_value()
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
                custom_key_converter: Callable[[Any], str] | None = None,
                **json_loads_kwargs) -> Cob:
    """Convert JSON text into a Cob instance via ``json.loads``.

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
        Cob: The converted Cob object.
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
