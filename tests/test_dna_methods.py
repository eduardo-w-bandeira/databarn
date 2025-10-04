"""
Comprehensive unit tests for the DNA class methods from databarn package.

This test suite covers:
- DNA class factory functionality (create_dna)
- Dual properties and methods behavior
- Grain setup and management (static and dynamic)
- Primary key properties and methods
- Keyring functionality and auto-generation
- Serialization methods (to_dict, to_json)
- Constraint validation and checking
- Parent-child relationships
- Barn management and integration
- Dynamic grain addition and removal
- Error handling for various constraint violations

The tests ensure that DNA correctly manages metadata and methods
for both static and dynamic Cob models.
"""

import pytest
import json
from typing import Any
from types import MappingProxyType
from databarn import Cob, Grain, Barn
from databarn.dna import create_dna
from databarn.exceptions import (
    ConstraintViolationError,
    GrainTypeMismatchError,
    CobConsistencyError,
    StaticModelViolationError
)
try:
    import typeguard
    HAS_TYPEGUARD = True
except ImportError:
    HAS_TYPEGUARD = False


class TestDnaClassFactory:
    """Test cases for DNA class factory functionality."""
    
    def test_create_dna_returns_class(self):
        """Test that create_dna returns a DNA class."""
        class TestModel(Cob):
            name: str = Grain()
        
        dna_class = create_dna(TestModel)
        
        assert isinstance(dna_class, type)
        assert dna_class.__name__ == 'Dna'
        assert dna_class.model == TestModel
        
    def test_dna_class_setup_static_model(self):
        """Test DNA class setup for static model with grains."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
            
        dna_class = Person.__dna__
        
        assert dna_class.model == Person
        assert dna_class.dynamic is False
        assert len(dna_class.label_grain_map) == 2
        assert 'name' in dna_class.label_grain_map
        assert 'age' in dna_class.label_grain_map
        
    def test_dna_class_setup_dynamic_model(self):
        """Test DNA class setup for dynamic model without grains."""
        class DynamicModel(Cob):
            pass
            
        dna_class = DynamicModel.__dna__
        
        assert dna_class.model == DynamicModel
        assert dna_class.dynamic is True
        assert len(dna_class.label_grain_map) == 0


class TestDnaProperties:
    """Test cases for DNA dual properties."""
    
    def test_grains_property(self):
        """Test grains property returns tuple of grain objects."""
        class Product(Cob):
            name: str = Grain()
            price: float = Grain()
            
        product = Product(name="Test", price=10.0)
        
        grains = product.__dna__.grains
        assert isinstance(grains, tuple)
        assert len(grains) == 2
        assert all(isinstance(grain, Grain) for grain in grains)
        
    def test_labels_property(self):
        """Test labels property returns tuple of grain labels."""
        class Book(Cob):
            title: str = Grain()
            author: str = Grain()
            isbn: str = Grain(pk=True)
            
        book = Book(title="Test Book", author="Test Author", isbn="123")
        
        labels = book.__dna__.labels
        assert isinstance(labels, tuple)
        assert len(labels) == 3
        assert 'title' in labels
        assert 'author' in labels
        assert 'isbn' in labels
        
    def test_primakey_labels_property(self):
        """Test primakey_labels property returns primary key labels."""
        class User(Cob):
            username: str = Grain(pk=True)
            email: str = Grain()
            password: str = Grain()
            
        user = User(username="test", email="test@example.com", password="pass")
        
        pk_labels = user.__dna__.primakey_labels
        assert isinstance(pk_labels, tuple)
        assert len(pk_labels) == 1
        assert pk_labels[0] == 'username'
        
    def test_primakey_labels_composite_key(self):
        """Test primakey_labels with composite primary key."""
        class Order(Cob):
            customer_id: int = Grain(pk=True)
            order_date: str = Grain(pk=True)
            amount: float = Grain()
            
        order = Order(customer_id=1, order_date="2023-01-01", amount=100.0)
        
        pk_labels = order.__dna__.primakey_labels
        assert isinstance(pk_labels, tuple)
        assert len(pk_labels) == 2
        assert 'customer_id' in pk_labels
        assert 'order_date' in pk_labels
        
    def test_primakey_defined_property(self):
        """Test primakey_defined property."""
        class WithPK(Cob):
            id: int = Grain(pk=True)
            name: str = Grain()
            
        class WithoutPK(Cob):
            name: str = Grain()
            
        with_pk = WithPK(id=1, name="test")
        without_pk = WithoutPK(name="test")
        
        assert with_pk.__dna__.primakey_defined is True
        assert without_pk.__dna__.primakey_defined is False
        
    def test_is_compos_primakey_property(self):
        """Test is_compos_primakey property."""
        class SimplePK(Cob):
            id: int = Grain(pk=True)
            
        class CompositePK(Cob):
            part1: str = Grain(pk=True)
            part2: str = Grain(pk=True)
            
        simple = SimplePK(id=1)
        composite = CompositePK(part1="a", part2="b")
        
        assert simple.__dna__.is_compos_primakey is False
        assert composite.__dna__.is_compos_primakey is True
        
    def test_primakey_len_property(self):
        """Test primakey_len property."""
        class NoPK(Cob):
            name: str = Grain()
            
        class SinglePK(Cob):
            id: int = Grain(pk=True)
            
        class CompositePK(Cob):
            id1: int = Grain(pk=True)
            id2: int = Grain(pk=True)
            
        no_pk = NoPK(name="test")
        single_pk = SinglePK(id=1)
        composite_pk = CompositePK(id1=1, id2=2)
        
        assert no_pk.__dna__.primakey_len == 1
        assert single_pk.__dna__.primakey_len == 1
        assert composite_pk.__dna__.primakey_len == 2


class TestDnaKeyring:
    """Test cases for DNA keyring functionality."""
    
    def test_keyring_with_single_primary_key(self):
        """Test keyring with single primary key."""
        class Item(Cob):
            id: int = Grain(pk=True)
            name: str = Grain()
            
        item = Item(id=42, name="test")
        
        assert item.__dna__.get_keyring() == 42
        
    def test_keyring_with_composite_primary_key(self):
        """Test keyring with composite primary key."""
        class CompositeItem(Cob):
            part1: str = Grain(pk=True)
            part2: int = Grain(pk=True)
            value: str = Grain()
            
        item = CompositeItem(part1="abc", part2=123, value="test")
        
        keyring = item.__dna__.get_keyring()
        assert isinstance(keyring, tuple)
        assert keyring == ("abc", 123)
        
    def test_keyring_without_primary_key_uses_autoid(self):
        """Test keyring falls back to autoid when no primary key defined."""
        class NoPKItem(Cob):
            name: str = Grain()
            
        item = NoPKItem(name="test")
        
        keyring = item.__dna__.get_keyring()
        assert isinstance(keyring, int)
        assert keyring == item.__dna__.autoid
        
    def test_autoid_is_object_id(self):
        """Test that autoid defaults to object id."""
        class TestItem(Cob):
            name: str = Grain()
            
        item = TestItem(name="test")
        
        assert item.__dna__.autoid == id(item)


class TestDnaSeeds:
    """Test cases for DNA seed management."""
    
    def test_seeds_property(self):
        """Test seeds property returns tuple of seed objects."""
        class TestModel(Cob):
            field1: str = Grain()
            field2: int = Grain()
            
        obj = TestModel(field1="test", field2=42)
        
        seeds = obj.__dna__.seeds
        assert isinstance(seeds, tuple)
        assert len(seeds) == 2
        
    def test_primakey_seeds_property(self):
        """Test primakey_seeds property."""
        class TestModel(Cob):
            id: int = Grain(pk=True)
            name: str = Grain()
            category: str = Grain(pk=True)
            
        obj = TestModel(id=1, name="test", category="A")
        
        pk_seeds = obj.__dna__.primakey_seeds
        assert isinstance(pk_seeds, tuple)
        assert len(pk_seeds) == 2

    def test_items_method(self):
        """Test items method returns label-value pairs."""
        class TestModel(Cob):
            name: str = Grain()
            age: int = Grain()
            
        obj = TestModel(name="test", age=25)
        
        items = list(obj.__dna__.items())
        assert len(items) == 2
        assert ('name', 'test') in items
        assert ('age', 25) in items

    def test_get_seed_method(self):
        """Test get_seed method."""
        class TestModel(Cob):
            name: str = Grain()
            age: int = Grain()
            
        obj = TestModel(name="test", age=25)
        
        name_seed = obj.__dna__.get_seed('name')
        assert name_seed.label == 'name'
        assert name_seed.get_value() == 'test'
        
    def test_get_seed_with_default(self):
        """Test get_seed method with default value."""
        class TestModel(Cob):
            name: str = Grain()
            
        obj = TestModel(name="test")
        
        # Existing seed
        existing = obj.__dna__.get_seed('name', 'default')
        assert existing.label == 'name'
        
        # Non-existing seed with default
        default_result = obj.__dna__.get_seed('nonexistent', 'default')
        assert default_result == 'default'
        
    def test_get_seed_keyerror_without_default(self):
        """Test get_seed raises KeyError for non-existent seed without default."""
        class TestModel(Cob):
            name: str = Grain()
            
        obj = TestModel(name="test")
        
        with pytest.raises(KeyError):
            obj.__dna__.get_seed('nonexistent')


class TestDnaDynamicGrains:
    """Test cases for dynamic grain management."""
    
    def test_add_grain_dynamically(self):
        """Test adding grain to dynamic model."""
        obj = Cob()  # Dynamic model
        
        grain = obj.__dna__.add_grain_dynamically('new_field')
        
        assert isinstance(grain, Grain)
        assert 'new_field' in obj.__dna__.label_grain_map
        assert obj.__dna__.get_seed('new_field') is not None
        
    def test_add_grain_dynamically_with_custom_grain(self):
        """Test adding custom grain to dynamic model."""
        obj = Cob()
        custom_grain = Grain(required=True)
        
        result_grain = obj.__dna__.add_grain_dynamically('custom_field', custom_grain)
        
        assert result_grain is custom_grain
        assert result_grain.required is True
        assert 'custom_field' in obj.__dna__.label_grain_map
        
    def test_add_grain_dynamically_to_static_model_fails(self):
        """Test that adding grain to static model fails."""
        class StaticModel(Cob):
            existing: str = Grain()
            
        obj = StaticModel(existing="test")
        
        with pytest.raises(StaticModelViolationError):
            obj.__dna__.add_grain_dynamically('new_field')
            
    def test_add_grain_dynamically_duplicate_label_fails(self):
        """Test that adding duplicate grain label fails."""
        obj = Cob()
        obj.__dna__.add_grain_dynamically('field1')
        
        with pytest.raises(CobConsistencyError):
            obj.__dna__.add_grain_dynamically('field1')


class TestDnaSerialization:
    """Test cases for DNA serialization methods."""
    
    def test_to_dict_simple(self):
        """Test to_dict with simple values."""
        class Person(Cob):
            name: str = Grain()
            age: int = Grain()
            
        person = Person(name="John", age=30)
        
        result = person.__dna__.to_dict()
        
        assert isinstance(result, dict)
        assert result == {"name": "John", "age": 30}
        
    def test_to_dict_with_key_names(self):
        """Test to_dict respects key settings."""
        class Person(Cob):
            full_name: str = Grain(key="name")
            years_old: int = Grain(key="age")
            
        person = Person(full_name="John", years_old=30)
        
        result = person.__dna__.to_dict()
        
        assert result == {"name": "John", "age": 30}
        
    def test_to_dict_with_nested_cob(self):
        """Test to_dict with nested Cob objects."""
        class Address(Cob):
            street: str = Grain()
            city: str = Grain()
            
        class Person(Cob):
            name: str = Grain()
            address: Address = Grain()
            
        address = Address(street="123 Main St", city="Anytown")
        person = Person(name="John", address=address)
        
        result = person.__dna__.to_dict()
        
        expected = {
            "name": "John",
            "address": {"street": "123 Main St", "city": "Anytown"}
        }
        assert result == expected
        
    def test_to_dict_with_barn(self):
        """Test to_dict with Barn objects."""
        class Item(Cob):
            name: str = Grain()
            quantity: int = Grain()
            
        class Order(Cob):
            order_id: int = Grain()
            items: Barn = Grain()
            
        items_barn = Barn(Item)
        items_barn.add(Item(name="Widget", quantity=5))
        items_barn.add(Item(name="Gadget", quantity=3))
        
        order = Order(order_id=1, items=items_barn)
        
        result = order.__dna__.to_dict()
        
        expected = {
            "order_id": 1,
            "items": [
                {"name": "Widget", "quantity": 5},
                {"name": "Gadget", "quantity": 3}
            ]
        }
        assert result == expected
        
    def test_to_json_simple(self):
        """Test to_json method."""
        class Data(Cob):
            value: int = Grain()
            name: str = Grain()
            
        data = Data(value=42, name="test")
        
        result = data.__dna__.to_json()
        
        parsed = json.loads(result)
        assert parsed == {"value": 42, "name": "test"}
        
    def test_to_json_with_kwargs(self):
        """Test to_json with json.dumps kwargs."""
        class Data(Cob):
            value: int = Grain()
            
        data = Data(value=42)
        
        result = data.__dna__.to_json(indent=2, sort_keys=True)
        
        assert "  " in result  # Check indentation
        parsed = json.loads(result)
        assert parsed == {"value": 42}


class TestDnaConstraintChecking:
    """Test cases for DNA constraint validation."""
    
    @pytest.mark.skipif(not HAS_TYPEGUARD, reason="typeguard not available")
    def test_check_constraints_type_validation(self):
        """Test constraint checking for type validation."""
        class TypedModel(Cob):
            number: int = Grain()
            
        obj = TypedModel()
        seed = obj.__dna__.get_seed('number')
        
        # Valid type should pass
        obj.__dna__._check_constrains(seed, 42)
        
        # Invalid type should raise error
        with pytest.raises(GrainTypeMismatchError):
            obj.__dna__._check_constrains(seed, "not a number")
            
    def test_check_constraints_required_validation(self):
        """Test constraint checking for required fields."""
        class RequiredModel(Cob):
            required_field: str = Grain(required=True)
            
        obj = RequiredModel(required_field="initial")
        seed = obj.__dna__.get_seed('required_field')
        
        # Valid value should pass
        obj.__dna__._check_constrains(seed, "valid")
        
        # None value should raise error for required field
        with pytest.raises(ConstraintViolationError):
            obj.__dna__._check_constrains(seed, None)
            
    def test_check_constraints_auto_validation(self):
        """Test constraint checking for auto fields."""
        class AutoModel(Cob):
            auto_field: int = Grain(auto=True)
            
        obj = AutoModel()
        seed = obj.__dna__.get_seed('auto_field')
        
        # Setting auto field should raise error
        with pytest.raises(ConstraintViolationError):
            obj.__dna__._check_constrains(seed, 42)
            
    def test_check_constraints_frozen_validation(self):
        """Test constraint checking for frozen fields."""
        class FrozenModel(Cob):
            frozen_field: str = Grain(frozen=True)
            
        obj = FrozenModel(frozen_field="initial")
        seed = obj.__dna__.get_seed('frozen_field')
        
        # Modifying frozen field should raise error
        with pytest.raises(ConstraintViolationError):
            obj.__dna__._check_constrains(seed, "new value")


class TestDnaParentChildRelationships:
    """Test cases for parent-child relationship management."""
    
    def test_set_parent_for_child_cob(self):
        """Test setting parent relationship for child Cob."""
        class Parent(Cob):
            name: str = Grain()
            child: "Child" = Grain()
            
        class Child(Cob):
            name: str = Grain()
            
        parent = Parent(name="Parent")
        child = Child(name="Child")
        
        # Set child
        parent.child = child
        
        assert child.__dna__.parent is parent
        
    def test_set_parent_for_child_barn(self):
        """Test setting parent relationship for child Barn."""
        class Parent(Cob):
            name: str = Grain()
            items: Barn = Grain()
            
        class Item(Cob):
            name: str = Grain()
            
        parent = Parent(name="Parent")
        barn = Barn(Item)
        
        # Set barn as child
        parent.items = barn
        
        assert barn.parent_cob is parent
        
    def test_remove_parent_when_changing_child(self):
        """Test that parent is removed when child value changes."""
        class Parent(Cob):
            child: "Child" = Grain()
            
        class Child(Cob):
            name: str = Grain()
            
        parent = Parent()
        child1 = Child(name="Child1")
        child2 = Child(name="Child2")
        
        # Set first child
        parent.child = child1
        assert child1.__dna__.parent is parent
        
        # Change to second child
        parent.child = child2
        assert child1.__dna__.parent is None
        assert child2.__dna__.parent is parent


class TestDnaBarnManagement:
    """Test cases for DNA barn management."""
    
    def test_add_barn(self):
        """Test adding barn to DNA."""
        class TestModel(Cob):
            name: str = Grain()
            
        obj = TestModel(name="test")
        barn = Barn(TestModel)
        
        obj.__dna__._add_barn(barn)
        
        assert barn in obj.__dna__.barns
        
    def test_add_duplicate_barn_fails(self):
        """Test that adding duplicate barn fails."""
        class TestModel(Cob):
            name: str = Grain()
            
        obj = TestModel(name="test")
        barn = Barn(TestModel)
        
        obj.__dna__._add_barn(barn)
        
        with pytest.raises(RuntimeError):
            obj.__dna__._add_barn(barn)
            
    def test_remove_barn(self):
        """Test removing barn from DNA."""
        class TestModel(Cob):
            name: str = Grain()
            
        obj = TestModel(name="test")
        barn = Barn(TestModel)
        
        obj.__dna__._add_barn(barn)
        assert barn in obj.__dna__.barns
        
        obj.__dna__._remove_barn(barn)
        assert barn not in obj.__dna__.barns
        
    def test_remove_nonexistent_barn_fails(self):
        """Test that removing non-existent barn fails."""
        class TestModel(Cob):
            name: str = Grain()
            
        obj = TestModel(name="test")
        barn = Barn(TestModel)
        
        with pytest.raises(RuntimeError):
            obj.__dna__._remove_barn(barn)


class TestDnaComparison:
    """Test cases for DNA comparison functionality."""
    
    def test_check_and_get_comparables_same_type(self):
        """Test getting comparables for same type objects."""
        class Person(Cob):
            name: str = Grain(comparable=True)
            age: int = Grain()
            
        person1 = Person(name="John", age=30)
        person2 = Person(name="Jane", age=25)
        
        comparables = person1.__dna__._check_and_get_comparables(person2)
        
        assert len(comparables) == 1
        assert comparables[0].label == 'name'
        
    def test_check_and_get_comparables_different_type_fails(self):
        """Test comparison fails for different types."""
        class Person(Cob):
            name: str = Grain(comparable=True)
            
        class Car(Cob):
            model: str = Grain()
            
        person = Person(name="John")
        car = Car(model="Toyota")
        
        with pytest.raises(CobConsistencyError):
            person.__dna__._check_and_get_comparables(car)
            
    def test_check_and_get_comparables_no_comparable_fields_fails(self):
        """Test comparison fails when no comparable fields exist."""
        class Person(Cob):
            name: str = Grain()  # Not comparable
            age: int = Grain()   # Not comparable
            
        person1 = Person(name="John", age=30)
        person2 = Person(name="Jane", age=25)
        
        with pytest.raises(CobConsistencyError):
            person1.__dna__._check_and_get_comparables(person2)


class TestDnaCreateBarn:
    """Test cases for DNA barn creation."""
    
    def test_create_barn_class_method(self):
        """Test create_barn class method."""
        class TestModel(Cob):
            name: str = Grain()
            
        barn = TestModel.__dna__.create_barn()
        
        assert isinstance(barn, Barn)
        assert barn.model is TestModel


class TestDnaAdvancedConstraints:
    """Test cases for advanced DNA constraint scenarios."""
    
    def test_check_constraints_pk_with_barn_fails(self):
        """Test that modifying PK after adding to barn fails."""
        class PKModel(Cob):
            id: int = Grain(pk=True)
            name: str = Grain()
            
        obj = PKModel(id=1, name="test")
        barn = Barn(PKModel)
        barn.add(obj)
        
        seed = obj.__dna__.get_seed('id')
        
        # Modifying PK when cob is in barn should raise error
        with pytest.raises(ConstraintViolationError):
            obj.__dna__._check_constrains(seed, 2)
            
    def test_check_constraints_unique_with_barn_fails(self):
        """Test that unique constraint is checked when cob is in barn."""
        class UniqueModel(Cob):
            email: str = Grain(unique=True)
            name: str = Grain()
            
        obj1 = UniqueModel(email="test@example.com", name="Test1")
        obj2 = UniqueModel(email="other@example.com", name="Test2")
        
        barn = Barn(UniqueModel)
        barn.add(obj1)
        barn.add(obj2)
        
        seed = obj2.__dna__.get_seed('email')
        
        # Setting duplicate unique value should raise error
        with pytest.raises(ConstraintViolationError):
            obj2.__dna__._check_constrains(seed, "test@example.com")
            
    def test_check_constraints_none_type_allowed(self):
        """Test that None values pass type checking."""
        class TypedModel(Cob):
            optional_number: int = Grain()
            
        obj = TypedModel()
        seed = obj.__dna__.get_seed('optional_number')
        
        # None should pass type checking
        obj.__dna__._check_constrains(seed, None)
        
    def test_check_constraints_auto_field_cannot_be_set(self):
        """Test that auto fields cannot be set to any value."""
        class AutoModel(Cob):
            auto_id: int = Grain(auto=True)
            
        obj = AutoModel()
        seed = obj.__dna__.get_seed('auto_id')
        
        # Auto field should not be settable to any value
        with pytest.raises(ConstraintViolationError):
            obj.__dna__._check_constrains(seed, 42)
            
        with pytest.raises(ConstraintViolationError):
            obj.__dna__._check_constrains(seed, None)


class TestDnaParentManagement:
    """Test cases for advanced parent-child relationship management."""
    
    def test_check_and_remove_parent_no_change(self):
        """Test that parent removal is skipped when value doesn't change."""
        class Parent(Cob):
            child: "Child" = Grain()
            
        class Child(Cob):
            name: str = Grain()
            
        parent = Parent()
        child = Child(name="Test")
        parent.child = child
        
        seed = parent.__dna__.get_seed('child')
        old_value = child
        
        # Should not remove parent if value is the same
        parent.__dna__._check_and_remove_parent(seed, old_value)
        
        assert child.__dna__.parent is parent
        
    def test_check_and_remove_parent_barn(self):
        """Test removing parent from barn when value changes."""
        class Parent(Cob):
            items: Barn = Grain()
            
        class Item(Cob):
            name: str = Grain()
            
        parent = Parent()
        barn = Barn(Item)
        parent.items = barn
        
        assert barn.parent_cob is parent
        
        # Change to different barn - this triggers the parent removal
        new_barn = Barn(Item)
        parent.items = new_barn  # This should remove parent from old barn
        
        # Original barn should have parent removed
        assert barn.parent_cob is None
        assert new_barn.parent_cob is parent


class TestDnaInitialization:
    """Test cases for DNA initialization and setup."""
    
    def test_dna_init_with_dynamic_model(self):
        """Test DNA initialization for dynamic model."""
        obj = Cob()
        dna = obj.__dna__
        
        assert dna.cob is obj
        assert dna.autoid == id(obj)
        assert dna.parent is None
        assert isinstance(dna.barns, list)
        assert len(dna.barns) == 0
        assert isinstance(dna.label_seed_map, dict)
        
    def test_dna_init_with_static_model(self):
        """Test DNA initialization for static model."""
        class StaticModel(Cob):
            field1: str = Grain()
            field2: int = Grain()
            
        obj = StaticModel(field1="test", field2=42)
        dna = obj.__dna__
        
        assert dna.cob is obj
        assert len(dna.label_seed_map) == 2
        # Static models have read-only seed maps
        assert isinstance(dna.label_seed_map, MappingProxyType)
        
    def test_dna_seeds_initialized_with_default(self):
        """Test that seeds are initialized with default values."""
        class TestModel(Cob):
            unset_field: str = Grain(default="default_value")
            optional_field: str = Grain()  # No default, will be None
            
        obj = TestModel()  # Don't set the fields
        
        # Field with default should have the default value
        default_seed = obj.__dna__.get_seed('unset_field')
        assert default_seed.get_value() == "default_value"
        
        # Field without default should be None
        optional_seed = obj.__dna__.get_seed('optional_field') 
        assert optional_seed.get_value() is None


class TestDnaWizardChildBarn:
    """Test cases for wizard child barn functionality."""
    
    def test_wiz_outer_model_grain_default_none(self):
        """Test that _outer_model_grain defaults to None."""
        class TestModel(Cob):
            name: str = Grain()
            
        assert TestModel.__dna__._outer_model_grain is None


class TestDnaEdgeCases:
    """Test cases for DNA edge cases and error scenarios."""
    
    def test_serialization_with_none_values(self):
        """Test serialization handles None values correctly."""
        class ModelWithNone(Cob):
            name: str = Grain()
            optional: str = Grain()
            
        obj = ModelWithNone(name="test", optional=None)
        
        result = obj.__dna__.to_dict()
        assert result == {"name": "test", "optional": None}
        
        json_result = obj.__dna__.to_json()
        parsed = json.loads(json_result)
        assert parsed == {"name": "test", "optional": None}
        
    def test_keyring_with_none_primary_key(self):
        """Test keyring behavior with None primary key values."""
        class NullablePK(Cob):
            id: int = Grain(pk=True)
            name: str = Grain()
            
        obj = NullablePK(id=None, name="test")
        
        # Should still return the None value
        assert obj.__dna__.get_keyring() is None
        
    def test_comparison_with_multiple_comparable_fields(self):
        """Test getting comparables with multiple comparable fields."""
        class MultiComparable(Cob):
            name: str = Grain(comparable=True)
            email: str = Grain(comparable=True)
            age: int = Grain()
            
        obj1 = MultiComparable(name="John", email="john@example.com", age=30)
        obj2 = MultiComparable(name="Jane", email="jane@example.com", age=25)
        
        comparables = obj1.__dna__._check_and_get_comparables(obj2)
        
        assert len(comparables) == 2
        comparable_labels = [seed.label for seed in comparables]
        assert 'name' in comparable_labels
        assert 'email' in comparable_labels
        
    def test_dual_property_behavior_class_vs_instance(self):
        """Test that dual properties work on both class and instance level."""
        class DualTest(Cob):
            field1: str = Grain()
            field2: int = Grain(pk=True)
            
        obj = DualTest(field1="test", field2=42)
        
        # Class level access
        class_grains = DualTest.__dna__.grains
        class_labels = DualTest.__dna__.labels
        
        # Instance level access
        instance_grains = obj.__dna__.grains  
        instance_labels = obj.__dna__.labels
        
        # Should be the same for static models
        assert class_grains == instance_grains
        assert class_labels == instance_labels


class TestDnaComprehensiveIntegration:
    """Comprehensive integration tests for DNA functionality."""
    
    def test_complete_dna_workflow(self):
        """Test a complete workflow using DNA functionality."""
        # Create a complex model with various grain types
        class Order(Cob):
            order_id: int = Grain(pk=True)
            customer_name: str = Grain(required=True, comparable=True)
            email: str = Grain(unique=True)
            total: float = Grain(frozen=True)
            created_at: str = Grain(auto=True)
            
        class OrderItem(Cob):
            product_name: str = Grain()
            quantity: int = Grain()
            price: float = Grain()
            
        # Test DNA properties
        assert Order.__dna__.primakey_defined is True
        assert Order.__dna__.is_compos_primakey is False
        assert Order.__dna__.primakey_len == 1
        assert len(Order.__dna__.grains) == 5
        
        # Create order instance
        order = Order(
            order_id=1001,
            customer_name="John Doe", 
            email="john@example.com",
            total=150.0
        )
        
        # Test keyring
        assert order.__dna__.get_keyring() == 1001
        
        # Test serialization
        order_dict = order.__dna__.to_dict()
        assert order_dict['order_id'] == 1001
        assert order_dict['customer_name'] == "John Doe"
        assert order_dict['email'] == "john@example.com"
        assert order_dict['total'] == 150.0
        
        # Test JSON serialization
        order_json = order.__dna__.to_json(indent=2)
        parsed_order = json.loads(order_json)
        assert parsed_order == order_dict
        
        # Test adding to barn
        orders_barn = Barn(Order)
        orders_barn.add(order)
        assert order in order.__dna__.barns[0]
        
        # Test nested structures
        class OrderWithItems(Cob):
            order_id: int = Grain(pk=True)
            items: Barn = Grain()
            
        items_barn = Barn(OrderItem)
        items_barn.add(OrderItem(product_name="Widget", quantity=2, price=25.0))
        items_barn.add(OrderItem(product_name="Gadget", quantity=1, price=100.0))
        
        complex_order = OrderWithItems(order_id=2001, items=items_barn)
        
        # Test nested serialization
        complex_dict = complex_order.__dna__.to_dict()
        assert complex_dict['order_id'] == 2001
        assert len(complex_dict['items']) == 2
        assert complex_dict['items'][0]['product_name'] == "Widget"
        assert complex_dict['items'][1]['product_name'] == "Gadget"
        
        # Test parent relationships
        assert items_barn.parent_cob is complex_order
        
    def test_dynamic_model_complete_workflow(self):
        """Test complete workflow with dynamic models."""
        # Create dynamic cob
        dynamic_obj = Cob()
        
        # Verify it's dynamic
        assert dynamic_obj.__dna__.dynamic is True
        
        # Add grains dynamically
        name_grain = dynamic_obj.__dna__.add_grain_dynamically('name', Grain(required=True))
        age_grain = dynamic_obj.__dna__.add_grain_dynamically('age', Grain(default=0))
        
        # Set values
        dynamic_obj.name = "Dynamic User"
        dynamic_obj.age = 25
        
        # Test properties
        assert len(dynamic_obj.__dna__.grains) == 2
        assert len(dynamic_obj.__dna__.labels) == 2
        assert 'name' in dynamic_obj.__dna__.labels
        assert 'age' in dynamic_obj.__dna__.labels
        
        # Test serialization
        dynamic_dict = dynamic_obj.__dna__.to_dict()
        assert dynamic_dict == {"name": "Dynamic User", "age": 25}
        
        # Test keyring (should use autoid since no PK defined)
        assert dynamic_obj.__dna__.get_keyring() == dynamic_obj.__dna__.autoid
        assert isinstance(dynamic_obj.__dna__.get_keyring(), int)
        
    def test_error_handling_comprehensive(self):
        """Test comprehensive error handling scenarios."""
        class StrictModel(Cob):
            id: int = Grain(pk=True)
            name: str = Grain(required=True)
            email: str = Grain(unique=True)
            status: str = Grain(frozen=True)
            created: str = Grain(auto=True)
            
        # Test multiple constraint violations
        obj = StrictModel(id=1, name="Test", email="test@example.com", status="active")
        
        # Add to barn to test pk and unique constraints
        barn = Barn(StrictModel)
        barn.add(obj)
        
        # Test PK constraint violation
        with pytest.raises(ConstraintViolationError, match="pk=True"):
            obj.id = 2
            
        # Test frozen constraint violation  
        with pytest.raises(ConstraintViolationError, match="frozen=True"):
            obj.status = "inactive"
            
        # Test auto constraint violation
        with pytest.raises(ConstraintViolationError, match="auto=True"):
            obj.created = "2023-01-01"
            
        # Test unique constraint with another object
        obj2 = StrictModel(id=2, name="Test2", email="other@example.com", status="pending")
        barn.add(obj2)
        
        with pytest.raises(ConstraintViolationError, match="unique"):
            obj2.email = "test@example.com"  # Duplicate email
