import json

import pytest

from databarn import Barn, Cob, one_to_many_grain, one_to_one_grain
from databarn.exceptions import BarnConstraintViolationError, DataBarnSyntaxError, GrainLabelError
from databarn.funcs import _key_to_label, _verify_label, dict_to_cob, json_to_cob


def test_key_to_label_applies_transformation_rules() -> None:
    assert _key_to_label(
        key="first name",
        replace_space_with="_",
        replace_dash_with="__",
        suffix_keyword_with="_",
        prefix_leading_num_with="n_",
        replace_invalid_char_with="_",
        suffix_existing_attr_with="_",
        custom_key_converter=None,
    ) == "first_name"

    assert _key_to_label(
        key="my-field",
        replace_space_with="_",
        replace_dash_with="__",
        suffix_keyword_with="_",
        prefix_leading_num_with="n_",
        replace_invalid_char_with="_",
        suffix_existing_attr_with="_",
        custom_key_converter=None,
    ) == "my__field"

    assert _key_to_label(
        key="1st-value",
        replace_space_with="_",
        replace_dash_with="__",
        suffix_keyword_with="_",
        prefix_leading_num_with="n_",
        replace_invalid_char_with="_",
        suffix_existing_attr_with="_",
        custom_key_converter=None,
    ) == "n_1st__value"

    assert _key_to_label(
        key="__dna__",
        replace_space_with="_",
        replace_dash_with="__",
        suffix_keyword_with="_",
        prefix_leading_num_with="n_",
        replace_invalid_char_with="_",
        suffix_existing_attr_with="_",
        custom_key_converter=None,
    ) == "__dna___"

    assert _key_to_label(
        key="anything",
        replace_space_with="_",
        replace_dash_with="__",
        suffix_keyword_with="_",
        prefix_leading_num_with="n_",
        replace_invalid_char_with="_",
        suffix_existing_attr_with="_",
        custom_key_converter=lambda value: f"x_{value}",
    ) == "x_anything"


def test_verify_label_rejects_collisions_and_invalid_identifiers() -> None:
    with pytest.raises(GrainLabelError):
        _verify_label("__dna__", "__dna__", {})

    with pytest.raises(GrainLabelError):
        _verify_label("name", "other-name", {"name": "first-name"})

    with pytest.raises(GrainLabelError):
        _verify_label("not valid", "not valid", {})


def test_dict_to_cob_preserves_keys_and_converts_nested_structures() -> None:
    class Payload(Cob):
        model_name: str

        @one_to_one_grain("response_format")
        class ResponseFormat(Cob):
            type: str

        @one_to_many_grain("messages")
        class Message(Cob):
            role: str
            content: str

    payload = dict_to_cob({
        "model name": "gpt-5",
        "response format": {"type": "json_object"},
        "messages": [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ],
    }, model=Payload)

    assert payload.model_name == "gpt-5"
    assert isinstance(payload.response_format, Payload.ResponseFormat)
    assert isinstance(payload.messages, Barn)
    assert [message.content for message in payload.messages] == ["hello", "world"]
    assert payload.__dna__.to_dict() == {
        "model name": "gpt-5",
        "response format": {"type": "json_object"},
        "messages": [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ],
    }


def test_dict_to_cob_rejects_label_collisions_and_non_string_converter_results() -> None:
    class Record(Cob):
        first_name: int

    with pytest.raises(GrainLabelError):
        dict_to_cob({"first name": 1, "first_name": 2}, model=Record)

    with pytest.raises(DataBarnSyntaxError):
        dict_to_cob({"value": 1}, custom_key_converter=lambda key: 42)


def test_dict_to_cob_rejects_mixed_child_barn_payloads() -> None:
    class Mailbox(Cob):
        subject: str

        @one_to_many_grain("messages")
        class Message(Cob):
            body: str

    with pytest.raises(BarnConstraintViolationError):
        dict_to_cob({
            "subject": "Inbox",
            "messages": [
                {"body": "hello"},
                "not-a-cob",
            ],
        }, model=Mailbox)


def test_get_grain_returns_default_for_missing_label() -> None:
    class Record(Cob):
        name: str

    assert Record.__dna__.get_grain("missing", default=None) is None


def test_json_to_cob_passes_json_loads_kwargs_through() -> None:
    class Record(Cob):
        value: object

    record = json_to_cob(
        json_str=json.dumps({"value": 1}),
        model=Record,
        parse_int=lambda raw: f"int:{raw}",
    )

    assert record.value == "int:1"