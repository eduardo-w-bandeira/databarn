import pytest
import json
from databarn import dict_to_cob, json_to_cob, Cob, Barn
from databarn.exceptions import InvalidGrainLabelError, DataBarnSyntaxError

def test_dict_to_cob_simple():
    """Test simple dictionary conversion."""
    data = {"name": "Test", "value": 123}
    cob = dict_to_cob(data)
    assert cob.name == "Test"
    assert cob.value == 123
    # Check if original keys are preserved
    assert cob.__dna__.to_dict() == data

def test_key_replacements_default():
    """Test default key replacements (spaces, dashes, numbers, etc)."""
    data = {
        "user name": "Alice",
        "kebab-case": "Value",
        "123start": "Number",
        "def": "Keyword",  # 'def' is a keyword
        "invalid@char": "Special"
    }
    cob = dict_to_cob(data)
    
    assert cob.user_name == "Alice"      # Space -> _
    assert cob.kebab__case == "Value"    # Dash -> __
    assert cob.n_123start == "Number"    # Leading num -> n_
    assert cob.def_ == "Keyword"         # Keyword -> suffix _
    assert cob.invalid_char == "Special" # @ -> _
    
    assert cob.__dna__.to_dict() == data

def test_dict_to_cob_with_model():
    """Test using `model` argument with custom Cob classes."""
    from databarn import Grain, create_child_cob_grain, create_child_barn_grain

    class Payload(Cob):
        model: str = Grain(required=True)
        temperature: float = Grain()
        max_tokens: int = Grain()
        reasoning_effort: str = Grain() # Reasoning effort is not supported in deepseek
        stream: bool = Grain(default=False)

        @create_child_cob_grain("response_format")
        class ResponseFormat(Cob):
            type: str = Grain("json_object")

        @create_child_barn_grain('messages')
        class Message(Cob):
            role: str = Grain(required=True)
            content: str = Grain(required=True)

    class Person(Cob):
        address: str = Grain()

        @create_child_cob_grain("natural")
        class Natural(Cob):
            first_name: str = Grain(required=True)
            last_name: str = Grain(required=True)
        
        @create_child_cob_grain("legal")
        class Legal(Cob):
            company_name: str = Grain(required=True)
            registration_number: str = Grain(required=True)

    # Test Payload
    payload_data = {
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 100,
        "reasoning_effort": "high",
        # stream uses default
        "response_format": {"type": "text"},
        "messages": [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"}
        ]
    }

    payload = dict_to_cob(payload_data, model=Payload)
    
    assert isinstance(payload, Payload)
    assert payload.model == "gpt-4"
    assert payload.temperature == 0.7
    assert payload.stream is False
    
    # Check nested Cob (response_format)
    assert isinstance(payload.response_format, Payload.ResponseFormat)
    assert payload.response_format.type == "text" 

    # Check nested Barn (messages)
    assert isinstance(payload.messages, Barn)
    assert len(payload.messages) == 2
    assert isinstance(payload.messages[0], Payload.Message)
    assert payload.messages[0].role == "user"
    assert payload.messages[0].content == "hello"

    # Test Person (Natural)
    person_natural_data = {
        "address": "123 St",
        "natural": {
            "first_name": "John",
            "last_name": "Doe"
        }
    }
    person_n = dict_to_cob(person_natural_data, model=Person)
    assert isinstance(person_n, Person)
    assert person_n.address == "123 St"
    assert isinstance(person_n.natural, Person.Natural)
    assert person_n.natural.first_name == "John"
    
    # Test Person (Legal)
    person_legal_data = {
        "address": "456 Ave",
        "legal": {
            "company_name": "Acme",
            "registration_number": "RGB-123"
        }
    }
    person_l = dict_to_cob(person_legal_data, model=Person)
    assert isinstance(person_l, Person)
    assert isinstance(person_l.legal, Person.Legal)
    assert person_l.legal.company_name == "Acme"


def test_custom_replacements():
    """Test custom replacement strings."""
    data = {
        "user name": "Alice",
        "kebab-case": "Value",
        "123start": "Number",
    }
    cob = dict_to_cob(
        data,
        replace_space_with="SPACE",
        replace_dash_with="DASH",
        prefix_leading_num_with="NUM"
    )
    
    assert cob.userSPACEname == "Alice"
    assert cob.kebabDASHcase == "Value"
    assert cob.NUM123start == "Number"

def test_custom_key_converter():
    """Test providing a custom key converter function."""
    def uppercase_keys(key):
        return key.upper()

    data = {"lower": 1, "case": 2}
    cob = dict_to_cob(data, custom_key_converter=uppercase_keys)
    
    assert cob.LOWER == 1
    assert cob.CASE == 2
    assert cob.__dna__.to_dict() == data

def test_custom_key_converter_error():
    """Test error when custom converter returns non-string."""
    def bad_converter(key):
        return 123 # Not a string

    with pytest.raises(DataBarnSyntaxError, match="must return a string"):
        dict_to_cob({"key": 1}, custom_key_converter=bad_converter)

def test_nested_dict_recursion():
    """Test recursive conversion of nested dictionaries."""
    data = {
        "parent": {
            "child": {
                "grandchild": "value"
            }
        }
    }
    cob = dict_to_cob(data)
    assert isinstance(cob.parent, Cob)
    assert isinstance(cob.parent.child, Cob)
    assert cob.parent.child.grandchild == "value"
    assert cob.__dna__.to_dict() == data

def test_list_of_dicts_to_barn():
    """Test that a list of dicts becomes a Barn."""
    data = {
        "items": [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"}
        ]
    }
    cob = dict_to_cob(data)
    assert isinstance(cob.items, Barn)
    assert len(cob.items) == 2
    assert cob.items[0].id == 1
    assert cob.items[1].name == "Item 2"
    
    # Verify to_dict roundtrip works for barns too
    assert cob.__dna__.to_dict() == data

def test_mixed_list_handling():
    """Test that a mixed list (cobs and primitives) remains a list."""
    data = {
        "mixed": [
            {"a": 1},
            "string",
            123
        ]
    }
    # Per implementation: items are converted individually.
    # {"a": 1} -> Cob
    # "string" -> "string"
    # only_cobs check will fail, so it should return a list
    cob = dict_to_cob(data)
    
    assert isinstance(cob.mixed, list)
    assert isinstance(cob.mixed[0], Cob)
    assert cob.mixed[0].a == 1
    assert cob.mixed[1] == "string"
    assert cob.__dna__.to_dict() == data

def test_conflict_existing_attr():
    """Test handling key collision with existing Cob attributes."""
    # __eq__ is a method on Cob
    data = {"__eq__": "value"}
    cob = dict_to_cob(data)
    # Default suffix_existing_attr_with is "_"
    assert cob.__eq___ == "value"

def test_key_collision_error():
    """Test that colliding keys raise InvalidGrainLabelError."""
    # "a b" -> "a_b"
    # "a_b" -> "a_b"
    data = {
        "a b": 1,
        "a_b": 2
    }
    with pytest.raises(InvalidGrainLabelError, match="Key conflict"):
        dict_to_cob(data)

def test_invalid_identifier_error():
    """Test that if a key cannot be made into a valid identifier, error is raised."""
    # Providing replacements that verify_label doesn't like? 
    # Or disabling replacements.
    data = {"123": "val"}
    # If we disable prefixing
    with pytest.raises(InvalidGrainLabelError, match="valid var name"):
        dict_to_cob(data, prefix_leading_num_with=None)

def test_json_to_cob():
    """Test json_to_cob wrapper."""
    json_str = '{"a": 1, "b": {"c": 2}}'
    cob = json_to_cob(json_str)
    assert cob.a == 1
    assert cob.b.c == 2
    
def test_json_to_cob_kwargs():
    """Test passing kwargs to json.loads via json_to_cob."""
    # Use something that requires specific json parsing, e.g. parse_float
    json_str = '{"val": 1.1}'
    def custom_float(x):
        return f"FLOAT:{x}"
    
    cob = json_to_cob(json_str, parse_float=custom_float)
    assert cob.val == "FLOAT:1.1"

def test_conflict_with_cob_methods():
    """Test collision with internal Cob methods/attributes if valid."""
    # As per README, __dna__ is protected.
    data = {"__dna__": "overwrite attempt"}
    # logic: `_key_to_label` checks `hasattr(_ref_cob, label)`.
    # `Cob` instances have `__dna__`.
    # So it should append suffix.
    cob = dict_to_cob(data)
    # Default suffix_existing_attr_with is "_"
    assert cob.__dna___ == "overwrite attempt"
    assert hasattr(cob, "__dna__") 

