import json

import pytest

from databarn import Barn, Cob, one_to_many_grain, one_to_one_grain
from databarn.constants import DNA_SYMBOL
from databarn.exceptions import SchemaValidationError, DataBarnSyntaxError, LabelValidationError
from databarn.funcs import _key_to_label, _verify_label, json_to_cob


def test_key_to_label_applies_transformation_rules() -> None:
    assert _key_to_label(
        key="first name",
        replace_space_with="_",
        replace_dash_with="_",
        suffix_keyword_with="_",
        prefix_leading_num_with="n_",
        replace_invalid_char_with="_",
        suffix_existing_attr_with="_",
        custom_key_converter=None,
    ) == "first_name"

    assert _key_to_label(
        key="my-field",
        replace_space_with="_",
        replace_dash_with="_",
        suffix_keyword_with="_",
        prefix_leading_num_with="n_",
        replace_invalid_char_with="_",
        suffix_existing_attr_with="_",
        custom_key_converter=None,
    ) == "my_field"

    assert _key_to_label(
        key="1st-value",
        replace_space_with="_",
        replace_dash_with="_",
        suffix_keyword_with="_",
        prefix_leading_num_with="n_",
        replace_invalid_char_with="_",
        suffix_existing_attr_with="_",
        custom_key_converter=None,
    ) == "n_1st_value"

    assert _key_to_label(
        key=DNA_SYMBOL,
        replace_space_with="_",
        replace_dash_with="_",
        suffix_keyword_with="_",
        prefix_leading_num_with="n_",
        replace_invalid_char_with="_",
        suffix_existing_attr_with="_",
        custom_key_converter=None,
    ) == DNA_SYMBOL + "_"

    assert _key_to_label(
        key="anything",
        replace_space_with="_",
        replace_dash_with="_",
        suffix_keyword_with="_",
        prefix_leading_num_with="n_",
        replace_invalid_char_with="_",
        suffix_existing_attr_with="_",
        custom_key_converter=lambda value: f"x_{value}",
    ) == "x_anything"


def test_key_to_label_covers_keyword_and_optional_transform_switches() -> None:
    assert _key_to_label(
        key="class",
        replace_space_with="_",
        replace_dash_with="_",
        suffix_keyword_with="_kw",
        prefix_leading_num_with="n_",
        replace_invalid_char_with="_",
        suffix_existing_attr_with="_",
        custom_key_converter=None,
    ) == "class_kw"

    assert _key_to_label(
        key="bad key-$",
        replace_space_with=None,
        replace_dash_with=None,
        suffix_keyword_with="_",
        prefix_leading_num_with=None,
        replace_invalid_char_with=None,
        suffix_existing_attr_with="_",
        custom_key_converter=None,
    ) == "bad key-$"

    assert _key_to_label(
        key="a$b",
        replace_space_with="_",
        replace_dash_with="_",
        suffix_keyword_with="_",
        prefix_leading_num_with="n_",
        replace_invalid_char_with="_",
        suffix_existing_attr_with="_",
        custom_key_converter=None,
    ) == "a_b"


def test_verify_label_rejects_collisions_and_invalid_identifiers() -> None:
    with pytest.raises(LabelValidationError):
        _verify_label("_dna_", "_dna_", {})

    with pytest.raises(LabelValidationError):
        _verify_label("name", "other-name", {"name": "first-name"})

    with pytest.raises(LabelValidationError):
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

    payload = Payload._dna_.create_cob_from_dict(dikt={
        "model name": "gpt-5",
        "response format": {"type": "json_object"},
        "messages": [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "world"},
        ],
    })

    assert payload.model_name == "gpt-5"
    assert isinstance(payload.response_format, Payload.ResponseFormat)
    assert isinstance(payload.messages, Barn)
    assert [message.content for message in payload.messages] == ["hello", "world"]
    assert payload._dna_.to_dict() == {
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

    with pytest.raises(LabelValidationError):
        Record._dna_.create_cob_from_dict(dikt={"first name": 1, "first_name": 2})

    with pytest.raises(DataBarnSyntaxError):
        Cob._dna_.create_cob_from_dict(dikt={"value": 1}, custom_key_converter=lambda key: 42)


def test_dict_to_cob_rejects_mixed_child_barn_payloads() -> None:
    class Mailbox(Cob):
        subject: str

        @one_to_many_grain("messages")
        class Message(Cob):
            body: str

    with pytest.raises(SchemaValidationError):
        Mailbox._dna_.create_cob_from_dict(dikt={
            "subject": "Inbox",
            "messages": [
                {"body": "hello"},
                "not-a-cob",
            ],
        })


def test_get_grain_returns_default_for_missing_label() -> None:
    class Record(Cob):
        name: str

    assert Record._dna_.get_grain("missing", default=None) is None


def test_json_to_cob_passes_json_loads_kwargs_through() -> None:
    class Record(Cob):
        value: object

    record = json_to_cob(
        json_str=json.dumps({"value": 1}),
        model=Record,
        parse_int=lambda raw: f"int:{raw}",
    )

    assert record.value == "int:1"


def test_dict_to_cob_rejects_non_dict_input() -> None:
    with pytest.raises(TypeError):
        Cob._dna_.create_cob_from_dict(dikt=[("name", "Ada")])  # type: ignore[arg-type]


def test_dict_to_cob_keeps_nested_dict_for_plain_dict_grain() -> None:
    class ConfigHolder(Cob):
        config: dict

    holder = ConfigHolder._dna_.create_cob_from_dict(dikt={"config": {"mode": "safe"}})

    assert isinstance(holder.config, dict)
    assert holder.config == {"mode": "safe"}


def test_dict_to_cob_converts_list_to_barn_for_barn_typed_grain() -> None:
    class Envelope(Cob):
        messages: Barn

    envelope = Envelope._dna_.create_cob_from_dict(dikt={"messages": [{"text": "hello"}]})

    assert isinstance(envelope.messages, Barn)
    first = envelope.messages[0]
    assert isinstance(first, Cob)
    assert first.text == "hello"


def test_dict_to_cob_keeps_list_for_non_barn_grain() -> None:
    class Envelope(Cob):
        messages: list

    envelope = Envelope._dna_.create_cob_from_dict(dikt={"messages": [{"text": "hello"}]})

    assert isinstance(envelope.messages, list)
    assert isinstance(envelope.messages[0], Cob)
    assert envelope.messages[0].text == "hello"


def test_dict_to_cob_dynamic_list_of_dicts_becomes_child_barn() -> None:
    cob = Cob._dna_.create_cob_from_dict(dikt={"messages": [{"text": "hello"}]})

    assert isinstance(cob.messages, Barn)
    assert cob.messages[0].text == "hello"


def test_dict_to_cob_dynamic_empty_list_remains_list() -> None:
    cob = Cob._dna_.create_cob_from_dict(dikt={"messages": []})

    assert isinstance(cob.messages, list)
    assert cob.messages == []


def test_dict_to_cob_skips_key_restore_for_absent_optional_grain() -> None:
    class Record(Cob):
        present: int
        optional: int

    record = Record._dna_.create_cob_from_dict(dikt={"present": 1})

    assert record.present == 1
    with pytest.raises(AttributeError):
        _ = record.optional