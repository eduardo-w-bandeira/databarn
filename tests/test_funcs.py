import pytest
import json
from databarn import dict_to_cob, json_to_cob, Cob, Barn, Grain, create_child_cob_grain, create_child_barn_grain
from databarn.exceptions import InvalidGrainLabelError, DataBarnSyntaxError, ConstraintViolationError, GrainTypeMismatchError

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


def test_model_constraint_required():
    """Test that dict_to_cob respects required=True constraint."""
    from databarn.exceptions import ConstraintViolationError
    
    class StrictModel(Cob):
        name: str = Grain(required=True)
        optional_field: str = Grain()
    
    # Valid data with required field
    valid_data = {"name": "John", "optional_field": "extra"}
    cob = dict_to_cob(valid_data, model=StrictModel)
    assert cob.name == "John"
    
    # Missing required field should raise error
    invalid_data = {"optional_field": "extra"}
    with pytest.raises(ConstraintViolationError, match="required=True"):
        dict_to_cob(invalid_data, model=StrictModel)
    
    # Explicitly setting required field to None should raise error
    none_data = {"name": None, "optional_field": "extra"}
    with pytest.raises(ConstraintViolationError, match="required=True"):
        dict_to_cob(none_data, model=StrictModel)


def test_model_constraint_type():
    """Test that dict_to_cob respects type constraints."""
    from databarn.exceptions import GrainTypeMismatchError
    
    class TypedModel(Cob):
        count: int = Grain()
        ratio: float = Grain()
        enabled: bool = Grain()
    
    # Valid types
    valid_data = {"count": 42, "ratio": 3.14, "enabled": True}
    cob = dict_to_cob(valid_data, model=TypedModel)
    assert cob.count == 42
    assert cob.ratio == 3.14
    assert cob.enabled is True
    
    # Wrong type for count
    wrong_type_data = {"count": "not_a_number", "ratio": 3.14, "enabled": True}
    with pytest.raises(GrainTypeMismatchError, match="int"):
        dict_to_cob(wrong_type_data, model=TypedModel)
    
    # Wrong type for ratio
    wrong_ratio_data = {"count": 42, "ratio": "not_a_float", "enabled": True}
    with pytest.raises(GrainTypeMismatchError, match="float"):
        dict_to_cob(wrong_ratio_data, model=TypedModel)


def test_model_constraint_default_values():
    """Test that dict_to_cob applies default values correctly."""
    class DefaultModel(Cob):
        name: str = Grain(required=True)
        status: str = Grain(default="active")
        count: int = Grain(default=0)
        enabled: bool = Grain(default=True)
    
    # Data with only required field
    minimal_data = {"name": "item"}
    cob = dict_to_cob(minimal_data, model=DefaultModel)
    assert cob.name == "item"
    assert cob.status == "active"
    assert cob.count == 0
    assert cob.enabled is True
    
    # Data overriding defaults
    override_data = {
        "name": "item",
        "status": "inactive",
        "count": 10,
        "enabled": False
    }
    cob2 = dict_to_cob(override_data, model=DefaultModel)
    assert cob2.status == "inactive"
    assert cob2.count == 10
    assert cob2.enabled is False


def test_model_constraint_factory():
    """Test that dict_to_cob respects factory constraints."""
    from databarn.exceptions import ConstraintViolationError
    
    class FactoryModel(Cob):
        items: list = Grain(factory=list)
        metadata: dict = Grain(factory=dict)
    
    # Factory creates default values on init
    cob1 = dict_to_cob({}, model=FactoryModel)
    assert cob1.items == []
    assert cob1.metadata == {}
    
    cob2 = dict_to_cob({}, model=FactoryModel)
    # Each instance should have its own list/dict (not shared)
    assert cob1.items is not cob2.items
    assert cob1.metadata is not cob2.metadata
    
    # Factory values cannot be overridden after initialization
    # This should raise a ConstraintViolationError
    cob3 = dict_to_cob({}, model=FactoryModel)
    with pytest.raises(ConstraintViolationError, match="factory"):
        cob3.items = [1, 2, 3]


def test_model_constraint_nested_required():
    """Test that required constraints work in nested models."""
    from databarn.exceptions import ConstraintViolationError
    
    class Person(Cob):
        name: str = Grain(required=True)
        @create_child_cob_grain("address")
        class PersonAddress(Cob):
            street: str = Grain(required=True)
            city: str = Grain(required=True)
            zipcode: str = Grain()
    
    # Valid nested data
    valid_data = {
        "name": "Alice",
        "address": {"street": "123 Main", "city": "NYC"}
    }
    cob = dict_to_cob(valid_data, model=Person)
    assert cob.name == "Alice"
    assert cob.address.street == "123 Main"
    
    # Missing required field in nested model should raise error
    invalid_nested = {
        "name": "Bob",
        "address": {"street": "456 Oak"}  # Missing required 'city'
    }
    with pytest.raises(ConstraintViolationError, match="required=True"):
        dict_to_cob(invalid_nested, model=Person)


def test_model_constraint_barn_required():
    """Test that required constraints work in barn (list) models."""
    from databarn.exceptions import ConstraintViolationError
    
    class Message(Cob):
        role: str = Grain(required=True)
        content: str = Grain(required=True)
    
    class Chat(Cob):
        title: str = Grain(required=True)
        @create_child_barn_grain() # Expected to create the label 'messages'
        class Message(Cob):
            role: str = Grain(required=True)
            content: str = Grain(required=True)
    
    # Valid data
    valid_data = {
        "title": "Conversation",
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"}
        ]
    }
    cob = dict_to_cob(valid_data, model=Chat)
    assert len(cob.messages) == 2
    assert cob.messages[1].content == "Hi"
    
    # Missing required field in barn item
    invalid_barn = {
        "title": "Conversation",
        "messages": [
            {"role": "user"},  # Missing required 'content'
            {"role": "assistant", "content": "Hi"}
        ]
    }
    with pytest.raises(ConstraintViolationError, match="required=True"):
        dict_to_cob(invalid_barn, model=Chat)


def test_model_constraint_comparable():
    """Test that models with comparable grains can be used for comparison."""
    class ComparableModel(Cob):
        id: int = Grain(comparable=True)
        name: str = Grain()  # Not comparable, default False
    
    data1 = {"id": 1, "name": "Alice"}
    data2 = {"id": 1, "name": "Bob"}
    data3 = {"id": 2, "name": "Alice"}
    
    cob1 = dict_to_cob(data1, model=ComparableModel)
    cob2 = dict_to_cob(data2, model=ComparableModel)
    cob3 = dict_to_cob(data3, model=ComparableModel)
    
    # Same id and comparable=True, different name
    # Comparison should only consider id (name is not comparable)
    assert cob1 == cob2  # Same id, name difference ignored
    assert cob1 != cob3  # Different id
    assert cob1 < cob3   # 1 < 2 

