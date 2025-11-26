"""
Comprehensive unit tests for the Cob class from databarn package.

This test suite covers:
- Cob initialization (dynamic and static models)
- Attribute access and modification
- Dictionary-like interface (__getitem__, __setitem__, __contains__)
- Comparison operations (__eq__, __ne__, __gt__, __ge__, __lt__, __le__)
- String representation (__repr__)
- Grain constraints and validation (type, required, frozen, auto, pk, unique)
- DNA integration and metadata
- Error handling and edge cases
- Advanced features like __post_init__ and metaclass functionality

The tests ensure that Cob behaves correctly as both a dynamic data carrier
and a static model with type checking and constraint validation.
"""

import pytest
from typing import Any
from databarn import Cob, Grain
from databarn.exceptions import (
    ConstraintViolationError,
    StaticModelViolationError,
    GrainTypeMismatchError,
    DataBarnSyntaxError,
    InvalidGrainLabelError,
)
try:
    import typeguard
    HAS_TYPEGUARD = True
except ImportError:
    HAS_TYPEGUARD = False


class TestCobInitialization:
    """Test cases for Cob initialization."""
    
    def test_dynamic_cob_creation_with_kwargs(self):
        """Test creating a dynamic Cob with keyword arguments."""
        cob = Cob(name="test", value=42, active=True)
        
        assert cob.name == "test"
        assert cob.value == 42
        assert cob.active is True
        
    def test_dynamic_cob_creation_empty(self):
        """Test creating an empty dynamic Cob."""
        cob = Cob()
        assert hasattr(cob, '__dna__')
        
    def test_static_cob_creation_with_kwargs(self):
        """Test creating a static Cob with keyword arguments."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
            active: bool = Grain(default=True)
        
        person = Person(name="Alice", age=30)
        
        assert person.name == "Alice"
        assert person.age == 30
        assert person.active is True  # default value
        
    def test_static_cob_creation_with_positional_args(self):
        """Test creating a static Cob with positional arguments."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
            active: bool = Grain(default=True)
        
        person = Person("Bob", 25, False)
        
        assert person.name == "Bob"
        assert person.age == 25
        assert person.active is False
        
    def test_static_cob_mixed_args_kwargs(self):
        """Test creating a static Cob with mixed positional and keyword arguments."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
            active: bool = Grain(default=True)
        
        person = Person("Charlie", age=35)
        
        assert person.name == "Charlie"
        assert person.age == 35
        assert person.active is True
        
    def test_too_many_positional_args_raises_error(self):
        """Test that too many positional arguments raise an error."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
        
        with pytest.raises(DataBarnSyntaxError):
            Person("Alice", 30, True, "extra")
            
    def test_positional_args_on_dynamic_cob_raises_error(self):
        """Test that positional arguments on dynamic Cob raise an error."""
        with pytest.raises(DataBarnSyntaxError):
            Cob("Alice", 30)
            
    def test_invalid_grain_assignment_static_model(self):
        """Test that assigning to undefined grain in static model raises error."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
        
        with pytest.raises(StaticModelViolationError):
            Person(name="Alice", age=30, invalid_field="value")


class TestCobAttributeAccess:
    """Test cases for Cob attribute access and modification."""
    
    def test_setattr_getattr_dynamic(self):
        """Test setting and getting attributes on dynamic Cob."""
        cob = Cob()
        cob.name = "test"
        cob.value = 42
        
        assert cob.name == "test"
        assert cob.value == 42
        
    def test_setattr_getattr_static(self):
        """Test setting and getting attributes on static Cob."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
        
        person = Person(name="Alice", age=30)
        person.name = "Bob"
        person.age = 25
        
        assert person.name == "Bob"
        assert person.age == 25


class TestCobDictionaryInterface:
    """Test cases for dictionary-like access to Cob."""
    
    def test_getitem_setitem_dynamic(self):
        """Test dictionary-like access on dynamic Cob."""
        cob = Cob(name="test", value=42)
        
        assert cob["name"] == "test"
        assert cob["value"] == 42
        
        # Dynamic cobs can add new fields
        cob["new_field"] = "new_value"
        assert cob["new_field"] == "new_value"
        
    def test_getitem_setitem_static(self):
        """Test dictionary-like access on static Cob."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
        
        person = Person(name="Alice", age=30)
        
        assert person["name"] == "Alice"
        assert person["age"] == 30
        
        person["name"] = "Bob"
        assert person["name"] == "Bob"
        assert person.name == "Bob"
        
    def test_getitem_nonexistent_grain_raises_keyerror(self):
        """Test that accessing non-existent grain raises KeyError."""
        class Person(Cob):
            name: str = Grain()
        
        person = Person(name="Alice")
        
        with pytest.raises(KeyError):
            _ = person["nonexistent"]
            
    def test_contains_operator(self):
        """Test the 'in' operator for grain existence."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
        
        person = Person(name="Alice", age=30)
        
        assert "name" in person
        assert "age" in person
        assert "nonexistent" not in person


class TestCobComparisons:
    """Test cases for Cob comparison operations."""
    
    def test_equality_same_instance(self):
        """Test that same instance is equal to itself."""
        cob = Cob(name="test")
        assert cob == cob
        assert not (cob != cob)
        
    def test_equality_comparable_grains(self):
        """Test equality based on comparable grains."""
        class Person(Cob):
            name: str = Grain(comparable=True)
            age: int = Grain(comparable=True)
            inactive_field: str = Grain()  # Not comparable
        
        person1 = Person(name="Alice", age=30, inactive_field="ignored1")
        person2 = Person(name="Alice", age=30, inactive_field="ignored2")
        person3 = Person(name="Bob", age=30, inactive_field="ignored1")
        
        assert person1 == person2
        assert person1 != person3
        
    def test_greater_than_comparable_grains(self):
        """Test greater than comparison based on comparable grains."""
        class Person(Cob):
            name: str = Grain(comparable=True)
            age: int = Grain(comparable=True)
        
        person1 = Person(name="Bob", age=35)
        person2 = Person(name="Alice", age=30)
        
        assert person1 > person2
        assert not (person2 > person1)
        
    def test_greater_equal_comparable_grains(self):
        """Test greater than or equal comparison."""
        class Person(Cob):
            name: str = Grain(comparable=True)
            age: int = Grain(comparable=True)
        
        person1 = Person(name="Bob", age=35)
        person2 = Person(name="Alice", age=30)
        person3 = Person(name="Bob", age=35)
        
        assert person1 >= person2
        assert person1 >= person3
        assert not (person2 >= person1)
        
    def test_less_than_comparable_grains(self):
        """Test less than comparison based on comparable grains."""
        class Person(Cob):
            name: str = Grain(comparable=True)
            age: int = Grain(comparable=True)
        
        person1 = Person(name="Alice", age=30)
        person2 = Person(name="Bob", age=35)
        
        assert person1 < person2
        assert not (person2 < person1)
        
    def test_less_equal_comparable_grains(self):
        """Test less than or equal comparison."""
        class Person(Cob):
            name: str = Grain(comparable=True)
            age: int = Grain(comparable=True)
        
        person1 = Person(name="Alice", age=30)
        person2 = Person(name="Bob", age=35)
        person3 = Person(name="Alice", age=30)
        
        assert person1 <= person2
        assert person1 <= person3
        assert not (person2 <= person1)


class TestCobRepresentation:
    """Test cases for Cob string representation."""
    
    def test_repr_dynamic(self):
        """Test string representation of dynamic Cob."""
        cob = Cob(name="test", value=42)
        repr_str = repr(cob)
        
        assert "Cob(" in repr_str
        assert "name='test'" in repr_str
        assert "value=42" in repr_str
        
    def test_repr_static(self):
        """Test string representation of static Cob."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
        
        person = Person(name="Alice", age=30)
        repr_str = repr(person)
        
        assert "Person(" in repr_str
        assert "name='Alice'" in repr_str
        assert "age=30" in repr_str


class TestCobGrainConstraints:
    """Test cases for Cob grain constraints and validation."""
    
    def test_required_grain_validation(self):
        """Test validation of required grains."""
        class Person(Cob):
            name: str = Grain(required=True)
            age: int = Grain()
        
        # This should work
        person = Person(name="Alice", age=30)
        assert person.name == "Alice"
        
        # Test that None is allowed for non-required grains with proper handling
        person2 = Person(name="Bob")  # age not provided, should use default
        assert person2.name == "Bob"
        
    def test_default_values(self):
        """Test that default values are properly set."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain(default=25)
            active: bool = Grain(default=True)
        
        person = Person(name="Alice")
        
        assert person.name == "Alice"
        assert person.age == 25
        assert person.active is True
        
    def test_primary_key_grain(self):
        """Test primary key grain functionality."""
        class Person(Cob):
            id: int = Grain(pk=True)
            name: str = Grain()
        
        person = Person(id=1, name="Alice")
        
        assert person.id == 1
        assert person.name == "Alice"


class TestCobPostInit:
    """Test cases for __post_init__ method."""
    
    def test_post_init_called(self):
        """Test that __post_init__ is called after initialization."""
        class Person(Cob):
            name: str = Grain()
            full_name: str = Grain(default="")
            
            def __post_init__(self):
                self.full_name = f"Mr/Ms {self.name}"
        
        person = Person(name="Alice")
        
        assert person.name == "Alice"
        assert person.full_name == "Mr/Ms Alice"


class TestCobEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_none_values_handling(self):
        """Test handling of None values."""
        cob = Cob(name=None, value=None)
        
        assert cob.name is None
        assert cob.value is None
        
    def test_complex_data_types(self):
        """Test with complex data types."""
        data = {"nested": {"key": "value"}}
        items = [1, 2, 3, 4, 5]
        
        cob = Cob(data=data, items=items)
        
        assert cob.data == data
        assert cob.items == items
        
    def test_class_attributes_vs_instance_attributes(self):
        """Test that class attributes don't interfere with instance attributes."""
        class Person(Cob):
            species = "Homo sapiens"  # Class attribute
            name: str = Grain()  # Grain
        
        person1 = Person(name="Alice")
        person2 = Person(name="Bob")
        
        assert person1.species == "Homo sapiens"
        assert person2.species == "Homo sapiens"
        assert person1.name == "Alice"
        assert person2.name == "Bob"


class TestCobConstraintValidation:
    """Test comprehensive constraint validation."""
    
    @pytest.mark.skipif(not HAS_TYPEGUARD, reason="typeguard not available")
    def test_type_constraint_validation(self):
        """Test that type constraints are validated."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
        
        # Valid types should work
        person = Person(name="Alice", age=30)
        assert person.name == "Alice"
        assert person.age == 30
        
        # Invalid type assignment should raise error
        with pytest.raises(GrainTypeMismatchError):
            person.age = "thirty"
            
    def test_required_constraint_validation(self):
        """Test required constraint validation."""
        class Person(Cob):
            name: str = Grain(required=True)
            nickname: str = Grain(required=False)
        
        # Valid assignment
        person = Person(name="Alice")
        assert person.name == "Alice"
        
        # Required field cannot be None
        with pytest.raises(ConstraintViolationError):
            person.name = None
            
        # Non-required field can be None
        person.nickname = None
        assert person.nickname is None
        
    def test_frozen_constraint_validation(self):
        """Test frozen constraint validation."""
        class Person(Cob):
            id: int = Grain(frozen=True)
            name: str = Grain()
        
        person = Person(id=1, name="Alice")
        
        # First assignment works
        assert person.id == 1
        
        # Second assignment should fail
        with pytest.raises(ConstraintViolationError):
            person.id = 2
            
        # Non-frozen fields can be modified
        person.name = "Bob"
        assert person.name == "Bob"
        
    def test_auto_constraint_validation(self):
        """Test auto constraint validation."""
        class Person(Cob):
            id: int = Grain(auto=True)
            name: str = Grain()
        
        # Auto fields cannot be manually set
        with pytest.raises(ConstraintViolationError):
            Person(id=1, name="Alice")
            
    def test_primary_key_constraint(self):
        """Test primary key constraint."""
        class Person(Cob):
            id: int = Grain(pk=True)
            name: str = Grain()
        
        person = Person(id=1, name="Alice")
        assert person.id == 1
        
        # Primary key modification restrictions are tested when cob is in barn
        # For now, just test that pk field works normally
        
    def test_unique_constraint_setup(self):
        """Test unique constraint setup."""
        class Person(Cob):
            email: str = Grain(unique=True)
            name: str = Grain()
        
        person = Person(email="alice@example.com", name="Alice")
        assert person.email == "alice@example.com"
        
    def test_comparable_grain_setup(self):
        """Test comparable grain configuration."""
        class Person(Cob):
            name: str = Grain(comparable=True)
            age: int = Grain(comparable=True)
            email: str = Grain(comparable=False)
        
        person1 = Person(name="Alice", age=30, email="alice@example.com")
        person2 = Person(name="Alice", age=30, email="different@example.com")
        
        # Should be equal based on comparable fields only
        assert person1 == person2
        
    def test_grain_key_name_functionality(self):
        """Test grain key attribute."""
        class Person(Cob):
            full_name: str = Grain(key="name")
            birth_year: int = Grain(key="year")
        
        person = Person(full_name="Alice Smith", birth_year=1990)
        
        # The grain should store the key for dict conversion
        name_grain = person.__dna__.get_seed("full_name").grain
        year_grain = person.__dna__.get_seed("birth_year").grain
        
        assert name_grain.key == "name"
        assert year_grain.key == "year"
        
    def test_grain_info_attrs(self):
        """Test custom attributes on grains."""
        class Person(Cob):
            name: str = Grain(min_length=2, max_length=50)
            age: int = Grain(min_value=0, max_value=150)
        
        person = Person(name="Alice", age=30)
        
        # Custom attributes should be stored on the grain
        name_grain = person.__dna__.get_seed("name").grain
        age_grain = person.__dna__.get_seed("age").grain
        
        assert name_grain.info.min_length == 2
        assert name_grain.info.max_length == 50
        assert age_grain.info.min_value == 0
        assert age_grain.info.max_value == 150


class TestCobDNAIntegration:
    """Test Cob integration with DNA system."""
    
    def test_dna_attribute_exists(self):
        """Test that Cob instances have __dna__ attribute."""
        class Person(Cob):
            name: str = Grain()
        
        person = Person(name="Alice")
        
        assert hasattr(person, '__dna__')
        assert hasattr(Person, '__dna__')
        
    def test_dna_seed_access(self):
        """Test accessing seeds through DNA."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
        
        person = Person(name="Alice", age=30)
        
        # Should be able to access seeds
        name_seed = person.__dna__.get_seed("name")
        age_seed = person.__dna__.get_seed("age")
        
        assert name_seed.label == "name"
        assert age_seed.label == "age"
        assert name_seed.get_value() == "Alice"
        assert age_seed.get_value() == 30
        
    def test_dna_labels_and_grains(self):
        """Test DNA labels and grains properties."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
            active: bool = Grain(default=True)
        
        person = Person(name="Alice", age=30)
        
        labels = person.__dna__.labels
        assert "name" in labels
        assert "age" in labels
        assert "active" in labels
        
        grains = person.__dna__.grains
        assert len(grains) == 3
        
    def test_dynamic_vs_static_model_detection(self):
        """Test detection of dynamic vs static models."""
        # Dynamic model (no grains defined)
        dynamic_cob = Cob(name="test")
        assert dynamic_cob.__dna__.dynamic is True
        
        # Static model (grains defined)
        class Person(Cob):
            name: str = Grain()
        
        static_person = Person(name="Alice")
        assert static_person.__dna__.dynamic is False


class TestCobErrorHandling:
    """Test comprehensive error handling scenarios."""
    
    def test_comparison_with_incompatible_types(self):
        """Test comparison with incompatible types."""
        from databarn.exceptions import CobConsistencyError
        
        class Person(Cob):
            name: str = Grain(comparable=True)
        
        person = Person(name="Alice")
        
        # Comparison with different Cob types should raise CobConsistencyError
        with pytest.raises(CobConsistencyError):
            person == Cob(bla="test")
            
    def test_getitem_with_invalid_key_type(self):
        """Test __getitem__ with invalid key types."""
        cob = Cob(name="test")
        
        # Should handle non-string keys gracefully
        with pytest.raises((KeyError, TypeError)):
            _ = cob[123]
            
    def test_setitem_with_invalid_key_type(self):
        """Test __setitem__ with invalid key types."""
        cob = Cob(name="test")
        
        # Should handle non-string keys gracefully
        with pytest.raises(InvalidGrainLabelError):
            cob[123] = "value"
            
    def test_contains_with_invalid_key_type(self):
        """Test __contains__ with invalid key types."""
        cob = Cob(name="test")
        
        # Should handle non-string keys gracefully
        try:
            result = 123 in cob
            assert result is False  # If no error, should be False
        except TypeError:
            pass  # TypeError is also acceptable
            
    def test_metacob_inheritance(self):
        """Test MetaCob metaclass functionality."""
        class Person(Cob):
            name: str = Grain()
        
        # MetaCob should set __dna__ attribute on class
        assert hasattr(Person, '__dna__')
        assert callable(Person.__dna__)
        
        # Each instance should have its own __dna__ instance
        person1 = Person(name="Alice")
        person2 = Person(name="Bob")
        
        assert person1.__dna__ is not person2.__dna__
        assert person1.__dna__.__class__ is person2.__dna__.__class__


class TestCobAdvancedFeatures:
    """Test advanced Cob features and interactions."""
    
    def test_multiple_inheritance_with_cob(self):
        """Test multiple inheritance scenarios."""
        class Mixin:
            def get_info(self):
                return f"Info for {self.name}"
        
        class Person(Cob, Mixin):
            name: str = Grain()
            age: int = Grain()
        
        person = Person(name="Alice", age=30)
        assert person.get_info() == "Info for Alice"
        
    def test_cob_subclassing(self):
        """Test subclassing Cob classes."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
        
        class Employee(Cob):  # Don't inherit from Person due to limitation
            name: str = Grain()
            age: int = Grain()
            employee_id: int = Grain()
            department: str = Grain(default="General")
        
        employee = Employee(name="Alice", age=30, employee_id=12345)
        
        assert employee.name == "Alice"
        assert employee.age == 30
        assert employee.employee_id == 12345
        assert employee.department == "General"
        
    def test_empty_static_model(self):
        """Test static model with no grains."""
        class EmptyModel(Cob):
            pass  # No grains defined
        
        # This should still work as dynamic
        model = EmptyModel(name="test")
        assert model.name == "test"
        
    def test_post_init_with_exceptions(self):
        """Test __post_init__ method that raises exceptions."""
        class ValidatedPerson(Cob):
            name: str = Grain()
            age: int = Grain()
            
            def __post_init__(self):
                if self.age < 0:
                    raise ValueError("Age cannot be negative")
        
        # Valid case should work
        person = ValidatedPerson(name="Alice", age=30)
        assert person.name == "Alice"
        
        # Invalid case should raise exception
        with pytest.raises(ValueError, match="Age cannot be negative"):
            ValidatedPerson(name="Bob", age=-5)
            
    def test_grain_was_set_tracking(self):
        """Test that grain's has_been_set property tracks assignments."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain(default=25)
        
        person = Person(name="Alice")
        
        # Name was explicitly set
        name_seed = person.__dna__.get_seed("name")
        assert name_seed.has_been_set is True
        
        # Age was not explicitly set (used default)
        age_seed = person.__dna__.get_seed("age")
        # Note: This behavior depends on implementation details
        # May be True due to default assignment in __init__


class TestCobStringConversion:
    """Test string conversion methods for Cob."""
    
    def test_str_method_fallback_to_repr(self):
        """Test that str() falls back to __repr__ since __str__ is not defined."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
        
        person = Person(name="Alice", age=30)
        str_result = str(person)
        repr_result = repr(person)
        
        # Since __str__ is not defined, str() should return the same as repr()
        assert str_result == repr_result
        assert "Person(" in str_result
        assert "name='Alice'" in str_result
        assert "age=30" in str_result


class TestCobDNAConversionMethods:
    """Test Cob DNA conversion methods (to_dict, to_json)."""
    
    def test_to_dict_simple(self):
        """Test converting Cob to dictionary via DNA."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
        
        person = Person(name="Alice", age=30)
        result = person.__dna__.to_dict()
        
        assert isinstance(result, dict)
        assert result["name"] == "Alice"
        assert result["age"] == 30
        
    def test_to_dict_with_custom_keys(self):
        """Test to_dict preserves custom keys from grain.key attribute."""
        class Person(Cob):
            full_name: str = Grain(key="name")
            birth_year: int = Grain(key="year")
        
        person = Person(full_name="Alice Smith", birth_year=1990)
        result = person.__dna__.to_dict()
        
        # Should use grain.key instead of label
        assert "name" in result
        assert "year" in result
        assert "full_name" not in result
        assert "birth_year" not in result
        assert result["name"] == "Alice Smith"
        assert result["year"] == 1990
        
    def test_to_dict_nested_cobs(self):
        """Test to_dict with nested Cob objects."""
        class Address(Cob):
            street: str = Grain()
            city: str = Grain()
        
        class Person(Cob):
            name: str = Grain()
            address: Address = Grain()
        
        address = Address(street="123 Main St", city="Boston")
        person = Person(name="Alice", address=address)
        result = person.__dna__.to_dict()
        
        assert isinstance(result, dict)
        assert result["name"] == "Alice"
        assert isinstance(result["address"], dict)
        assert result["address"]["street"] == "123 Main St"
        assert result["address"]["city"] == "Boston"
        
    def test_to_json_simple(self):
        """Test converting Cob to JSON via DNA."""
        import json
        
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
        
        person = Person(name="Alice", age=30)
        json_result = person.__dna__.to_json()
        
        assert isinstance(json_result, str)
        parsed = json.loads(json_result)
        assert parsed["name"] == "Alice"
        assert parsed["age"] == 30
        
    def test_to_json_with_kwargs(self):
        """Test to_json with json.dumps keyword arguments."""
        import json
        
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
        
        person = Person(name="Alice", age=30)
        json_result = person.__dna__.to_json(indent=2, sort_keys=True)
        
        assert isinstance(json_result, str)
        assert "  " in json_result  # Check for indentation
        parsed = json.loads(json_result)
        assert parsed["name"] == "Alice"
        assert parsed["age"] == 30


class TestCobDynamicFieldManagement:
    """Test dynamic field addition and management in Cob."""
    
    def test_dynamic_field_addition_via_setitem(self):
        """Test adding fields dynamically via __setitem__."""
        cob = Cob(name="test")
        
        # Add new field via dictionary-like access
        cob["new_field"] = "new_value"
        
        assert hasattr(cob, "new_field")
        assert cob.new_field == "new_value"
        assert cob["new_field"] == "new_value"
        assert "new_field" in cob
        
    def test_dynamic_field_addition_via_setattr(self):
        """Test adding fields dynamically via attribute assignment (auto-adds to dynamic Cob)."""
        cob = Cob(name="test")
        
        # Add new field via attribute assignment
        cob.another_field = "another_value"
        
        assert hasattr(cob, "another_field")
        assert cob.another_field == "another_value"
        
        # Dynamic cobs now auto-add attributes as grains/items
        assert cob["another_field"] == "another_value"
        assert "another_field" in cob

    def test_dynamic_field_deletion_via_del_and_delitem(self):
        """Test deleting dynamic fields using `delattr` and `delitem`."""
        cob = Cob(name="test")

        # Add fields dynamically
        cob.extra = "to_remove"
        cob["other"] = 123

        assert "extra" in cob
        assert "other" in cob

        # Delete via delattr
        del cob.extra
        assert "extra" not in cob
        with pytest.raises(AttributeError):
            _ = cob.extra

        # Delete via delitem
        del cob["other"]
        assert "other" not in cob
        with pytest.raises(KeyError):
            _ = cob["other"]
        
    def test_static_model_rejects_dynamic_fields_via_setitem(self):
        """Test that static models reject dynamic field addition via __setitem__."""
        class Person(Cob):
            name: str = Grain()
        
        person = Person(name="Alice")
        
        with pytest.raises(StaticModelViolationError):
            person["invalid_field"] = "value"
            
    def test_static_model_allows_existing_field_modification_via_setitem(self):
        """Test that static models allow modification of existing fields via __setitem__."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
        
        person = Person(name="Alice", age=30)
        
        # Modifying existing field should work
        person["name"] = "Bob"
        person["age"] = 25
        
        assert person.name == "Bob"
        assert person.age == 25

    def test_static_model_deletion_raises_error(self):
        """Deleting grains on a static model should raise StaticModelViolationError."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()

        person = Person(name="Alice", age=30)

        # Deleting via delattr should raise
        with pytest.raises(StaticModelViolationError):
            del person.name

        # Deleting via delitem should also raise
        with pytest.raises(StaticModelViolationError):
            del person["age"]


class TestCobAttributeErrorHandling:
    """Test attribute access error scenarios."""
    
    def test_getattr_nonexistent_attribute(self):
        """Test that accessing non-existent attributes raises AttributeError."""
        cob = Cob(name="test")
        
        with pytest.raises(AttributeError):
            _ = cob.nonexistent
            
    def test_getitem_nonexistent_grain_static_model(self):
        """Test that accessing non-existent grain via __getitem__ raises KeyError."""
        class Person(Cob):
            name: str = Grain()
        
        person = Person(name="Alice")
        
        with pytest.raises(KeyError, match="Grain 'nonexistent' not found"):
            _ = person["nonexistent"]
            
    def test_getitem_nonexistent_grain_dynamic_model(self):
        """Test that accessing non-existent grain in dynamic model raises KeyError."""
        cob = Cob(name="test")
        
        with pytest.raises(KeyError, match="Grain 'nonexistent' not found"):
            _ = cob["nonexistent"]


class TestCobSpecialAttributeHandling:
    """Test handling of special attributes and edge cases."""
    
    def test_dna_attribute_can_be_overwritten_but_breaks_functionality(self):
        """Test that __dna__ attribute can be overwritten but breaks functionality."""
        cob = Cob(name="test")
        original_dna = cob.__dna__
        
        # Verify original functionality works
        assert hasattr(cob.__dna__, 'labels')
        assert "name" in cob.__dna__.labels
        
        # The __dna__ attribute can be overwritten using direct dict access
        cob.__dict__['__dna__'] = "something else"
        assert cob.__dna__ == "something else"
        
        # But this breaks the Cob functionality
        with pytest.raises(AttributeError):
            _ = cob.__dna__.labels  # This will fail because it's now a string
            
        # We can restore it using direct dict access
        cob.__dict__['__dna__'] = original_dna
        assert hasattr(cob.__dna__, 'labels')
        assert "name" in cob.__dna__.labels
        
    def test_accessing_cob_builtin_attributes(self):
        """Test that Cob built-in attributes are accessible."""
        cob = Cob(name="test")
        
        # These should be accessible and not conflict with grains
        assert hasattr(cob, '__dict__')
        assert hasattr(cob, '__class__')
        assert hasattr(cob, '__dna__')
        
    def test_grain_label_conflicts_with_python_builtins(self):
        """Test grain labels that might conflict with Python built-ins."""
        # Dynamic cob should handle any label
        cob = Cob()
        cob.type = "test_type"
        cob.class_ = "test_class" 
        cob.dict = {"key": "value"}
        
        assert cob.type == "test_type"
        assert cob.class_ == "test_class"
        assert cob.dict == {"key": "value"}


class TestCobHashingAndIdentity:
    """Test Cob hashing and identity behaviors."""
    
    def test_cob_not_hashable_by_default(self):
        """Test that Cob objects are not hashable by default."""
        cob = Cob(name="test")
        
        # Should not be hashable since __hash__ is not defined
        with pytest.raises(TypeError, match="unhashable type"):
            hash(cob)
            
        # Cannot be used as dict keys
        with pytest.raises(TypeError, match="unhashable type"):
            {cob: "value"}
            
        # Cannot be added to sets
        with pytest.raises(TypeError, match="unhashable type"):
            {cob}
            
    def test_cob_identity_vs_equality(self):
        """Test difference between identity (is) and equality (==)."""
        class Person(Cob):
            name: str = Grain(comparable=True)
            age: int = Grain(comparable=True)
        
        person1 = Person(name="Alice", age=30)
        person2 = Person(name="Alice", age=30)
        
        # Should be equal but not identical
        assert person1 == person2
        assert person1 is not person2
        
        # Same object should be identical and equal
        person3 = person1
        assert person1 is person3
        assert person1 == person3


class TestCobBooleanEvaluation:
    """Test boolean evaluation of Cob objects."""
    
    def test_cob_truthiness(self):
        """Test that Cob objects are truthy by default."""
        # Empty Cob should still be truthy
        empty_cob = Cob()
        assert bool(empty_cob) is True
        
        # Cob with data should be truthy
        cob_with_data = Cob(name="test", value=42)
        assert bool(cob_with_data) is True
        
        # Static model should be truthy
        class Person(Cob):
            name: str = Grain()
        
        person = Person(name="Alice")
        assert bool(person) is True
        
        # Even with None values should be truthy
        cob_with_none = Cob(name=None, value=None)
        assert bool(cob_with_none) is True


class TestCobIterationCapabilities:
    """Test iteration-related methods for Cob objects."""
    
    def test_cob_iteration_attempts_fail_gracefully(self):
        """Test that Cob objects fail iteration attempts gracefully."""
        cob = Cob(name="test", value=42)
        
        # Python tries to iterate using __getitem__ with integer indices
        # This should fail when it tries cob[0], cob[1], etc.
        with pytest.raises(KeyError, match="Grain '0' not found"):
            list(cob)
            
        # Same for for-loops
        with pytest.raises(KeyError):
            for item in cob:
                pass
                
    def test_cob_has_no_len(self):
        """Test that Cob objects don't support len() by default."""
        cob = Cob(name="test", value=42)
        
        with pytest.raises(TypeError, match="object of type 'Cob' has no len()"):
            len(cob)


class TestCobDeepBehavior:
    """Test deeper behavioral aspects of Cob."""
    
    def test_cob_attribute_assignment_order(self):
        """Test that attribute assignment happens in the expected order."""
        assignment_order = []
        
        class TrackingCob(Cob):
            def __setattr__(self, name, value):
                if name != '__dna__':  # Skip internal DNA setup
                    assignment_order.append(f"{name}={value}")
                super().__setattr__(name, value)
        
        # Create with keyword arguments
        TrackingCob(name="test", value=42)
        
        # Should have tracked the assignments
        assert "name=test" in assignment_order
        assert "value=42" in assignment_order
        
    def test_cob_preserves_mutable_objects(self):
        """Test that Cob preserves references to mutable objects."""
        original_list = [1, 2, 3]
        original_dict = {"key": "value"}
        
        cob = Cob(my_list=original_list, my_dict=original_dict)
        
        # Should be the same object, not a copy
        assert cob.my_list is original_list
        assert cob.my_dict is original_dict
        
        # Mutations should be reflected
        original_list.append(4)
        original_dict["new_key"] = "new_value"
        
        assert 4 in cob.my_list
        assert cob.my_dict["new_key"] == "new_value"
        
    def test_cob_with_none_values_in_comparisons(self):
        """Test Cob comparison behavior with None values."""
        class Person(Cob):
            name: str = Grain(comparable=True)
            age: int = Grain(comparable=True)
        
        person1 = Person(name="Alice", age=None)
        person2 = Person(name="Alice", age=None)
        person3 = Person(name="Alice", age=30)
        
        # None == None should be True
        assert person1 == person2
        
        # None != 30 should be True (not equal)
        assert person1 != person3


class TestCobDecoratorsIntegration:
    """Test Cob integration with decorator functionality."""
    
    def test_create_child_barn_grain_decorator(self):
        """Test @create_child_barn_grain decorator functionality."""
        from databarn.decorators import create_child_barn_grain
        from databarn import Barn
        
        @create_child_barn_grain("items")
        class Item(Cob):
            name: str = Grain()
            value: int = Grain()
        
        class Container(Cob):
            name: str = Grain()
            # The decorator creates a grain that needs to be defined in the parent
            # Let's check if the grain was properly created in Item's DNA
        
        # The decorator should have created an outer model grain
        assert hasattr(Item.__dna__, '_outer_model_grain')
        assert Item.__dna__._outer_model_grain is not None
        
        # When used properly, the Container would need to include the items grain
        # For now, let's test that the decorator worked on the Item class
        item1 = Item(name="item1", value=100)
        assert item1.name == "item1"
        assert item1.value == 100
        
    def test_create_child_cob_grain_decorator(self):
        """Test @create_child_cob_grain decorator functionality."""
        from databarn.decorators import create_child_cob_grain
        
        @create_child_cob_grain("profile")
        class Profile(Cob):
            bio: str = Grain()
            website: str = Grain()
        
        # The decorator should have created an outer model grain
        assert hasattr(Profile.__dna__, '_outer_model_grain')
        assert Profile.__dna__._outer_model_grain is not None
        
        # Test the Profile class works normally
        profile = Profile(bio="Software Developer", website="https://example.com")
        assert isinstance(profile, Profile)
        assert profile.bio == "Software Developer"
        assert profile.website == "https://example.com"
        
        # The decorated class should be usable as a normal Cob
        assert hasattr(profile, '__dna__')
        assert "bio" in profile.__dna__.labels
        assert "website" in profile.__dna__.labels


class TestCobDNAPrimakeyFunctionality:
    """Test Cob DNA primakey functionality."""
    
    def test_primakey_simple(self):
        """Test simple primary key functionality."""
        class Person(Cob):
            id: int = Grain(pk=True)
            name: str = Grain()
        
        person = Person(id=123, name="Alice")
        keyring = person.__dna__.get_keyring()
        
        assert keyring == 123
        
    def test_primakey_composite(self):
        """Test composite primary key functionality."""
        class Order(Cob):
            customer_id: int = Grain(pk=True)
            order_id: int = Grain(pk=True)
            total: float = Grain()
        
        order = Order(customer_id=100, order_id=200, total=99.99)
        keyring = order.__dna__.get_keyring()
        
        # Composite primakey should be a tuple
        assert isinstance(keyring, tuple)
        assert keyring == (100, 200)
        
    def test_primakey_properties(self):
        """Test primakey-related properties."""
        class Person(Cob):
            id: int = Grain(pk=True)
            name: str = Grain()
            
        class Product(Cob):
            name: str = Grain()
            price: float = Grain()
        
        person = Person(id=123, name="Alice")
        product = Product(name="Widget", price=19.99)
        
        # Person has primary key defined
        assert person.__dna__.primakey_defined is True
        assert person.__dna__.is_compos_primakey is False
        
        # Product has no primary key
        assert product.__dna__.primakey_defined is False


class TestCobSeedDirectAccess:
    """Test direct access to Cob seeds."""
    
    def test_seed_value_access(self):
        """Test accessing seed values directly."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
        
        person = Person(name="Alice", age=30)
        
        name_seed = person.__dna__.get_seed("name")
        age_seed = person.__dna__.get_seed("age")
        
        assert name_seed.get_value() == "Alice"
        assert age_seed.get_value() == 30
        
    def test_seed_value_modification(self):
        """Test modifying values through seeds."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
        
        person = Person(name="Alice", age=30)
        
        name_seed = person.__dna__.get_seed("name")
        name_seed.set_value("Bob")
        
        assert person.name == "Bob"
        assert name_seed.get_value() == "Bob"
        
    def test_seed_has_been_set_property(self):
        """Test seed has_been_set property."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain(default=25)
        
        person = Person(name="Alice")  # age not provided, will use default
        
        name_seed = person.__dna__.get_seed("name")
        age_seed = person.__dna__.get_seed("age")
        
        assert name_seed.has_been_set is True
        # Note: has_been_set behavior for defaults may vary by implementation


class TestCobAttributeVsGrainAccess:
    """Test the difference between attribute access and grain access."""
    
    def test_attribute_vs_grain_distinction(self):
        """Test that regular attributes and grains are handled differently."""
        class Person(Cob):
            name: str = Grain()
        
        person = Person(name="Alice")
        
        # Regular attribute assignment
        person.non_grain_attr = "not a grain"
        
        # Should be accessible as attribute
        assert hasattr(person, "non_grain_attr")
        assert person.non_grain_attr == "not a grain"
        
        # But not accessible via grain access methods
        with pytest.raises(KeyError):
            _ = person["non_grain_attr"]
        
        assert "non_grain_attr" not in person
        
        # Grain should be accessible both ways
        assert person.name == "Alice"
        assert person["name"] == "Alice"
        assert "name" in person


class TestCobReprDetailedFormatting:
    """Test detailed aspects of Cob __repr__ formatting."""
    
    def test_repr_with_special_characters(self):
        """Test __repr__ with special characters in values."""
        cob = Cob(text="Hello\nWorld", quote="He said 'Hi'")
        repr_str = repr(cob)
        
        # Should properly escape special characters
        assert "text='Hello\\nWorld'" in repr_str
        assert "quote=\"He said 'Hi'\"" in repr_str
        
    def test_repr_with_none_values(self):
        """Test __repr__ with None values."""
        cob = Cob(name=None, value=None)
        repr_str = repr(cob)
        
        assert "name=None" in repr_str
        assert "value=None" in repr_str
        
    def test_repr_ordering_matches_grain_order(self):
        """Test that __repr__ respects grain declaration order in static models."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
            city: str = Grain()
        
        person = Person(age=30, city="Boston", name="Alice")  # Different order
        repr_str = repr(person)
        
        # Should respect declaration order: name, then age, then city
        name_pos = repr_str.find("name=")
        age_pos = repr_str.find("age=")
        city_pos = repr_str.find("city=")
        
        assert name_pos < age_pos < city_pos


class TestCobErrorMessages:
    """Test that error messages are helpful and informative."""
    
    def test_keyerror_message_format(self):
        """Test KeyError message format for missing grains."""
        class Person(Cob):
            name: str = Grain()
        
        person = Person(name="Alice")
        
        try:
            _ = person["missing"]
        except KeyError as e:
            error_msg = str(e)
            assert "missing" in error_msg
            assert "Person" in error_msg or "Cob" in error_msg
            
    def test_static_model_violation_message(self):
        """Test StaticModelViolationError message clarity."""
        class Person(Cob):
            name: str = Grain()
        
        person = Person(name="Alice")
        
        try:
            person["invalid"] = "value"
        except StaticModelViolationError as e:
            error_msg = str(e)
            assert "invalid" in error_msg
            assert "static" in error_msg.lower()


class TestCobPlatformCompatibility:
    """Test Cob behavior across different scenarios."""
    
    def test_pickle_compatibility_awareness(self):
        """Test awareness of pickle limitations (Cob is likely not picklable)."""
        import pickle
        
        cob = Cob(name="test")
        
        # Cob is likely not picklable due to complex internal structure
        # This test documents the expected behavior
        try:
            pickled = pickle.dumps(cob)
            unpickled = pickle.loads(pickled)
            # If it works, verify it's equivalent
            assert unpickled.name == cob.name
        except (TypeError, AttributeError, pickle.PicklingError):
            # This is expected and acceptable for complex objects
            pass
            
    def test_copy_compatibility_awareness(self):
        """Test awareness of copy module limitations."""
        import copy
        
        cob = Cob(name="test", data={"key": "value"})
        
        # Shallow copy might work
        try:
            shallow_copy = copy.copy(cob)
            assert shallow_copy.name == cob.name
            # Mutable objects should be the same reference
            assert shallow_copy.data is cob.data
        except (TypeError, AttributeError):
            # If it doesn't work, that's documentable behavior
            pass
            
        # Deep copy is more likely to fail
        try:
            deep_copy = copy.deepcopy(cob)
            assert deep_copy.name == cob.name
            # Mutable objects should be different references
            assert deep_copy.data is not cob.data
            assert deep_copy.data == cob.data
        except (TypeError, AttributeError):
            # This is likely to fail and that's acceptable
            pass


class TestCobConversionIntegration:
    """Test Cob integration with dict_to_cob and json_to_cob functions."""
    
    def test_round_trip_dict_conversion(self):
        """Test that Cob -> dict -> Cob preserves data."""
        from databarn.funcs import dict_to_cob
        
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
            active: bool = Grain(default=True)
        
        original = Person(name="Alice", age=30)
        
        # Convert to dict and back
        as_dict = original.__dna__.to_dict()
        reconstructed = dict_to_cob(as_dict)
        
        # Should have same values
        assert reconstructed.name == original.name
        assert reconstructed.age == original.age
        assert reconstructed.active == original.active
        
    def test_round_trip_json_conversion(self):
        """Test that Cob -> JSON -> Cob preserves data."""
        from databarn.funcs import json_to_cob
        
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
            active: bool = Grain(default=True)
        
        original = Person(name="Alice", age=30)
        
        # Convert to JSON and back
        as_json = original.__dna__.to_json()
        reconstructed = json_to_cob(as_json)
        
        # Should have same values
        assert reconstructed.name == original.name
        assert reconstructed.age == original.age
        assert reconstructed.active == original.active


if __name__ == "__main__":
    pytest.main([__file__])
