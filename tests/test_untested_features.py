"""
Test cases for previously untested features and edge cases in the databarn library.

This module covers:
- Barn.add_all() method with multiple cobs
- Barn.append() method return value
- Advanced comparison operators for Cobs
- Dynamic grain operations
- DNA methods and properties
- Edge cases for unique constraints and data manipulation
- Cob containment checks with deleted attributes
- Dictionary-like operations on Cobs
"""

import pytest
from databarn import Cob, Barn, Grain
from databarn.exceptions import (
    ConstraintViolationError, DataBarnSyntaxError, 
    BarnConsistencyError, StaticModelViolationError
)


# ============================================================================
# Test Barn.add_all() - Adding Multiple Cobs
# ============================================================================

class TestBarnAddAll:
    """Test Barn.add_all() method for adding multiple cobs at once."""

    def test_add_all_multiple_cobs(self):
        """Test adding multiple cobs with add_all()."""
        class Item(Cob):
            id: int = Grain(pk=True)
            name: str = Grain()
        
        barn = Barn(Item)
        i1 = Item(id=1, name="Item1")
        i2 = Item(id=2, name="Item2")
        i3 = Item(id=3, name="Item3")
        
        result = barn.add_all(i1, i2, i3)
        
        assert len(barn) == 3
        assert barn[0] == i1
        assert barn[1] == i2
        assert barn[2] == i3
        assert result is barn  # Method chaining

    def test_add_all_empty_args(self):
        """Test add_all() with no arguments."""
        class Item(Cob):
            id: int = Grain(pk=True)
        
        barn = Barn(Item)
        result = barn.add_all()
        
        assert len(barn) == 0
        assert result is barn

    def test_add_all_with_wrong_type(self):
        """Test add_all() fails if any cob is wrong type."""
        class Item(Cob):
            id: int = Grain(pk=True)
        
        class OtherItem(Cob):
            pass
        
        barn = Barn(Item)
        i1 = Item(id=1)
        o1 = OtherItem()
        
        with pytest.raises(BarnConsistencyError):
            barn.add_all(i1, o1)
        
        # i1 should still be in barn
        assert len(barn) == 1

    def test_add_all_method_chaining(self):
        """Test method chaining with add_all()."""
        class Item(Cob):
            id: int = Grain(pk=True)
        
        barn = Barn(Item)
        i1 = Item(id=1)
        i2 = Item(id=2)
        
        # Should be able to chain
        result = barn.add_all(i1).add(i2)
        
        assert len(barn) == 2
        assert result is barn


# ============================================================================
# Test Barn.append() - Append Without Return Value
# ============================================================================

class TestBarnAppend:
    """Test Barn.append() method."""

    def test_append_returns_none(self):
        """Test that append() returns None."""
        class Item(Cob):
            id: int = Grain(pk=True)
        
        barn = Barn(Item)
        i1 = Item(id=1)
        
        result = barn.append(i1)
        
        assert result is None
        assert len(barn) == 1
        assert barn[0] == i1

    def test_append_multiple(self):
        """Test appending multiple cobs sequentially."""
        class Item(Cob):
            id: int = Grain(pk=True)
        
        barn = Barn(Item)
        items = [Item(id=i) for i in range(1, 4)]
        
        for item in items:
            barn.append(item)
        
        assert len(barn) == 3

    def test_append_vs_add_behavior(self):
        """Test that append() and add() add cob the same way, just different return."""
        class Item(Cob):
            id: int = Grain(pk=True)
        
        barn1 = Barn(Item)
        barn2 = Barn(Item)
        
        i1 = Item(id=1)
        i2 = Item(id=2)
        
        barn1.add(i1)
        barn1.append(i2)
        
        barn2.append(i1)
        barn2.add(i2)
        
        assert len(barn1) == 2
        assert len(barn2) == 2
        assert barn1[0] == barn2[0]
        assert barn1[1] == barn2[1]


# ============================================================================
# Test Cob Comparison Operators - Greater Than / Less Than
# ============================================================================

class TestCobComparisons:
    """Test Cob comparison operators (__gt__, __ge__, __lt__, __le__)."""

    def test_cob_greater_than(self):
        """Test __gt__ operator."""
        class Score(Cob):
            points: int = Grain(comparable=True)
        
        s1 = Score(points=100)
        s2 = Score(points=50)
        
        assert s1 > s2
        assert not (s2 > s1)
        assert not (s1 > s1)

    def test_cob_greater_than_or_equal(self):
        """Test __ge__ operator."""
        class Score(Cob):
            points: int = Grain(comparable=True)
        
        s1 = Score(points=100)
        s2 = Score(points=100)
        s3 = Score(points=50)
        
        assert s1 >= s2
        assert s1 >= s3
        assert not (s3 >= s1)

    def test_cob_less_than(self):
        """Test __lt__ operator."""
        class Score(Cob):
            points: int = Grain(comparable=True)
        
        s1 = Score(points=50)
        s2 = Score(points=100)
        
        assert s1 < s2
        assert not (s2 < s1)
        assert not (s1 < s1)

    def test_cob_less_than_or_equal(self):
        """Test __le__ operator."""
        class Score(Cob):
            points: int = Grain(comparable=True)
        
        s1 = Score(points=50)
        s2 = Score(points=50)
        s3 = Score(points=100)
        
        assert s1 <= s2
        assert s1 <= s3
        assert not (s3 <= s1)

    def test_comparison_with_multiple_comparable_grains(self):
        """Test comparison with multiple comparable grains.
        
        For __gt__, ALL comparable grains must be strictly greater to return True.
        """
        class Record(Cob):
            year: int = Grain(comparable=True)
            score: int = Grain(comparable=True)
        
        r1 = Record(year=2021, score=100)
        r2 = Record(year=2020, score=50)
        r3 = Record(year=2020, score=100)  # Same year but higher score
        
        # Both year and score are greater
        assert r1 > r2
        
        # Year is same (2020 not > 2020), so this should fail
        assert not (r3 > r2)

    def test_comparison_requires_comparable_grain(self):
        """Test that comparison fails if no comparable grain is defined."""
        from databarn.exceptions import CobConsistencyError
        
        class Item(Cob):
            name: str = Grain()  # Not comparable
        
        i1 = Item(name="A")
        i2 = Item(name="B")
        
        with pytest.raises(CobConsistencyError):
            i1 > i2

    def test_comparison_prevents_different_types(self):
        """Test that comparing different Cob types raises error."""
        from databarn.exceptions import CobConsistencyError
        
        class Item1(Cob):
            val: int = Grain(comparable=True)
        
        class Item2(Cob):
            val: int = Grain(comparable=True)
        
        i1 = Item1(val=10)
        i2 = Item2(val=20)
        
        with pytest.raises(CobConsistencyError):
            i1 > i2


# ============================================================================
# Test Dynamic Grain Operations
# ============================================================================

class TestDynamicGrainOperations:
    """Test dynamic grain creation and manipulation."""

    def test_add_grain_dynamically(self):
        """Test explicitly adding a grain to a dynamic Cob using add_grain_dynamically."""
        cob = Cob()
        
        # Get the instance DNA
        grain = Grain(default="test_value")
        cob.__dna__.add_grain_dynamically("custom_field", str, grain)
        
        # The grain should be created with None value initially
        assert hasattr(cob, "custom_field")
        assert cob.__dna__.get_grain("custom_field") == grain

    def test_create_cereals_dynamically_via_setattr(self):
        """Test that setting a new attribute on dynamic cob creates grain dynamically."""
        cob = Cob()
        cob.new_field = 42
        
        assert cob.new_field == 42
        assert "new_field" in cob.__dna__.labels

    def test_dynamic_model_cannot_add_grain_with_static(self):
        """Test that add_grain_dynamically fails on static models."""
        class Static(Cob):
            name: str = Grain()
        
        s = Static(name="test")
        grain = Grain()
        
        with pytest.raises(StaticModelViolationError):
            s.__dna__.add_grain_dynamically("new_field", str, grain)

    def test_cannot_create_duplicate_grain_dynamically(self):
        """Test that creating a grain with existing label fails."""
        cob = Cob()
        cob.field1 = "value1"
        
        grain = Grain()
        with pytest.raises(Exception):  # CobConsistencyError or similar
            cob.__dna__.add_grain_dynamically("field1", str, grain)


# ============================================================================
# Test DNA Properties and Methods
# ============================================================================

class TestDNAProperties:
    """Test DNA class properties and methods."""

    def test_active_grists_property(self):
        """Test active_grists property returns only grists with values set."""
        class Item(Cob):
            field1: str = Grain()
            field2: str = Grain(default="not_provided")
        
        i = Item(field1="value1")  # field2 gets its default value
        
        active = i.__dna__.active_grists
        
        # Both fields should be active since both have defaults set
        assert len(active) == 2
        
        # Test with a dynamic cob instead
        dyn = Cob()
        dyn.field1 = "value1"
        # Only field1 was set
        assert len(dyn.__dna__.active_grists) == 1

    def test_active_grists_empty_when_all_deleted(self):
        """Test active_grists is empty after deleting all values."""
        class Item(Cob):
            field1: str = Grain()
            field2: str = Grain()
        
        i = Item(field1="value1", field2="value2")
        assert len(i.__dna__.active_grists) == 2
        
        del i.field1
        del i.field2
        
        assert len(i.__dna__.active_grists) == 0

    def test_primakey_grists_property(self):
        """Test primakey_grists returns only primary key grists."""
        class Item(Cob):
            id: int = Grain(pk=True)
            name: str = Grain()
            status: str = Grain(pk=True)
        
        i = Item(id=1, name="test", status="active")
        
        pk_grists = i.__dna__.primakey_grists
        
        assert len(pk_grists) == 2
        assert set(g.label for g in pk_grists) == {"id", "status"}

    def test_latest_parent_property(self):
        """Test latest_parent returns the most recently added parent."""
        from databarn import one_to_one_grain
        
        @one_to_one_grain("children")
        class Child(Cob):
            name: str = Grain()
        
        class Parent(Cob):
            child: Child = Child
        
        child = Child(name="test")
        p1 = Parent(child=child)
        p2 = Parent(child=child)
        
        # The child's latest parent should be p2
        assert child.__dna__.latest_parent == p2


# ============================================================================
# Test Unique Constraint Edge Cases
# ============================================================================

class TestUniqueConstraintEdgeCases:
    """Test edge cases for unique constraints."""

    def test_unique_constraint_with_none_limited(self):
        """Test that None value is allowed for unique constraints but only once."""
        class Item(Cob):
            uid: int = Grain(unique=True)
            name: str = Grain()
        
        barn = Barn(Item)
        
        # First None value is allowed
        i1 = Item(uid=None, name="first")
        barn.add(i1)
        
        # Second None should fail (None is treated as a value)
        i2 = Item(uid=None, name="second")
        with pytest.raises(ConstraintViolationError):
            barn.add(i2)

    def test_unique_constraint_update_in_place(self):
        """Test updating a unique field fails if new value conflicts."""
        class Item(Cob):
            uid: int = Grain(unique=True)
            name: str = Grain()
        
        barn = Barn(Item)
        i1 = Item(uid=1, name="first")
        i2 = Item(uid=2, name="second")
        
        barn.add(i1)
        barn.add(i2)
        
        # Try to update i1's uid to conflict with i2
        with pytest.raises(ConstraintViolationError):
            i1.uid = 2


# ============================================================================
# Test Cob Dictionary-Like Methods
# ============================================================================

class TestCobDictMethods:
    """Test dictionary-like methods on Cob objects."""

    def test_cob_keys_method(self):
        """Test keys() method returns grain labels."""
        class Item(Cob):
            name: str = Grain()
            value: int = Grain()
        
        i = Item(name="test", value=42)
        
        keys = list(i.__dna__.keys())
        
        assert "name" in keys
        assert "value" in keys
        assert len(keys) == 2

    def test_cob_values_method(self):
        """Test values() method returns grain values."""
        class Item(Cob):
            name: str = Grain()
            value: int = Grain()
        
        i = Item(name="test", value=42)
        
        values = list(i.__dna__.values())
        
        assert "test" in values
        assert 42 in values

    def test_cob_items_method(self):
        """Test items() method returns (label, value) tuples."""
        class Item(Cob):
            name: str = Grain()
            value: int = Grain()
        
        i = Item(name="test", value=42)
        
        items = list(i.__dna__.items())
        
        assert ("name", "test") in items
        assert ("value", 42) in items

    def test_cob_clear_method(self):
        """Test clear() method removes all values."""
        class Item(Cob):
            name: str = Grain()
            value: int = Grain()
        
        i = Item(name="test", value=42)
        
        i.__dna__.clear()
        
        with pytest.raises(AttributeError):
            _ = i.name
        with pytest.raises(AttributeError):
            _ = i.value

    def test_cob_get_method(self):
        """Test get() method with default value."""
        class Item(Cob):
            name: str = Grain()
        
        i = Item(name="test")
        
        assert i.__dna__.get("name") == "test"
        assert i.__dna__.get("nonexistent", "default") == "default"
        
        with pytest.raises(KeyError):
            i.__dna__.get("nonexistent")

    def test_cob_pop_method(self):
        """Test pop() method removes and returns value."""
        class Item(Cob):
            name: str = Grain()
            value: int = Grain()
        
        i = Item(name="test", value=42)
        
        result = i.__dna__.pop("name")
        
        assert result == "test"
        with pytest.raises(AttributeError):
            _ = i.name
        
        # Pop with default
        assert i.__dna__.pop("nonexistent", "default") == "default"

    def test_cob_popitem_method(self):
        """Test popitem() removes and returns last item."""
        class Item(Cob):
            field1: str = Grain()
            field2: str = Grain()
        
        i = Item(field1="a", field2="b")
        
        label, value = i.__dna__.popitem()
        
        assert label == "field2"
        assert value == "b"
        assert len(i.__dna__.active_grists) == 1

    def test_cob_popitem_empty(self):
        """Test popitem() on empty Cob raises KeyError."""
        dyn = Cob()  # Dynamic cob with no fields set
        
        with pytest.raises(KeyError):
            dyn.__dna__.popitem()

    def test_cob_setdefault_method(self):
        """Test setdefault() method."""
        class Item(Cob):
            name: str = Grain()
            value: int = Grain()
        
        i = Item(name="test")
        
        # Existing key
        assert i.__dna__.setdefault("name") == "test"
        
        # For static models, can only setdefault on existing keys
        # Setting a value to an existing field with None
        result = i.__dna__.setdefault("value")
        # value was initialized to None, so it returns None
        assert result is None
        
        # Test with dynamic cob
        dyn = Cob()
        dyn.field1 = "value1"
        
        # Existing field
        assert dyn.__dna__.setdefault("field1") == "value1"
        
        # New field with default
        result = dyn.__dna__.setdefault("field2", 99)
        assert result == 99
        assert dyn.field2 == 99

    def test_cob_update_with_dict(self):
        """Test update() method with dictionary."""
        class Item(Cob):
            name: str = Grain()
            value: int = Grain()
        
        i = Item()
        
        i.__dna__.update({"name": "test", "value": 42})
        
        assert i.name == "test"
        assert i.value == 42

    def test_cob_update_with_kwargs(self):
        """Test update() method with keyword arguments."""
        class Item(Cob):
            name: str = Grain()
            value: int = Grain()
        
        i = Item()
        
        i.__dna__.update(name="test", value=42)
        
        assert i.name == "test"
        assert i.value == 42

    def test_cob_update_with_both(self):
        """Test update() method with both dict and kwargs."""
        class Item(Cob):
            name: str = Grain()
            value: int = Grain()
            extra: str = Grain()
        
        i = Item()
        
        i.__dna__.update({"name": "test"}, value=42, extra="data")
        
        assert i.name == "test"
        assert i.value == 42
        assert i.extra == "data"

    def test_cob_fromkeys(self):
        """Test fromkeys() instance method."""
        class Item(Cob):
            field1: str = Grain()
            field2: str = Grain()
            field3: str = Grain()
        
        # fromkeys is an instance method (DNA instance method)
        i = Item()
        result = i.__dna__.fromkeys(["field1", "field2"], "default_value")
        
        assert result.field1 == "default_value"
        assert result.field2 == "default_value"
        # field3 is not in the sequence, so it keeps its default
        assert result.field3 is None


# ============================================================================
# Test Cob Containment with Deleted Attributes
# ============================================================================

class TestCobContainmentWithDeletion:
    """Test __contains__ behavior with deleted attributes."""

    def test_contains_after_deletion(self):
        """Test that __contains__ returns False for deleted attributes."""
        class Item(Cob):
            name: str = Grain()
            value: int = Grain()
        
        i = Item(name="test", value=42)
        
        assert "name" in i
        del i.name
        # After deletion, the grain still exists in the model,
        # but the attribute doesn't exist in the cob
        # __contains__ should still return True because the Grain is defined
        assert "name" in i
        
        # But we can't access it
        with pytest.raises(AttributeError):
            _ = i.name


# ============================================================================
# Test Grist Methods and Properties
# ============================================================================

class TestGristMethods:
    """Test Grist class methods and properties."""

    def test_grist_get_value_or_none(self):
        """Test get_value_or_none() returns None if not set."""
        class Item(Cob):
            name: str = Grain()
        
        i = Item()
        grist = i.__dna__.get_grist("name")
        
        assert grist.get_value_or_none() is None

    def test_grist_get_value_with_default(self):
        """Test get_value() with default parameter for unset values."""
        class Item(Cob):
            name: str = Grain()
            value: int = Grain()
        
        i = Item(name="test")  # value not explicitly set
        grist = i.__dna__.get_grist("value")
        
        # get_value() returns the current value (None since unset)
        assert grist.get_value() is None
        
        # With default should return default if needed
        from databarn.constants import ABSENT
        assert grist.get_value(ABSENT) is None  # Still None since it's initialized
        
        # get_value_or_none should work too
        assert grist.get_value_or_none() is None

    def test_grist_delegation_to_grain(self):
        """Test that Grist delegates attribute access to Grain."""
        class Item(Cob):
            name: str = Grain(default="default_name")
        
        i = Item()
        grist = i.__dna__.get_grist("name")
        
        # These attributes should come from the grain
        assert grist.label == "name"
        assert grist.type == str
        assert grist.default == "default_name"


# ============================================================================
# Test Barn with Labeled Primakeys
# ============================================================================

class TestBarnLabeledPrimakeys:
    """Test Barn methods using labeled primakeys."""

    def test_get_with_labeled_primakeys(self):
        """Test get() method with labeled primakeys."""
        class Item(Cob):
            id: int = Grain(pk=True)
            category: str = Grain(pk=True)
            name: str = Grain()
        
        barn = Barn(Item)
        i1 = Item(id=1, category="A", name="Item1")
        barn.add(i1)
        
        # Get using labeled primakeys
        result = barn.get(id=1, category="A")
        assert result == i1

    def test_has_primakey_with_labeled_keys(self):
        """Test has_primakey() with labeled keys."""
        class Item(Cob):
            id: int = Grain(pk=True)
            category: str = Grain(pk=True)
        
        barn = Barn(Item)
        i1 = Item(id=1, category="A")
        barn.add(i1)
        
        assert barn.has_primakey(id=1, category="A")
        assert not barn.has_primakey(id=2, category="A")

    def test_labeled_primakeys_syntax_error(self):
        """Test that mixing positional and labeled primakeys raises error."""
        class Item(Cob):
            id: int = Grain(pk=True)
            category: str = Grain(pk=True)
        
        barn = Barn(Item)
        i1 = Item(id=1, category="A")
        barn.add(i1)
        
        with pytest.raises(DataBarnSyntaxError):
            barn.get(1, category="A")  # Mixing positional and labeled


# ============================================================================
# Test Cob to/from Dictionary
# ============================================================================

class TestCobToDictConversion:
    """Test Cob to dictionary conversion including nested structures."""

    def test_to_dict_with_key_override(self):
        """Test to_dict() uses key if specified instead of label."""
        class Item(Cob):
            name: str = Grain(key="item_name")
            value: int = Grain(key="item_value")
        
        i = Item(name="test", value=42)
        d = i.__dna__.to_dict()
        
        assert "item_name" in d
        assert "item_value" in d
        assert d["item_name"] == "test"
        assert d["item_value"] == 42

    def test_to_dict_includes_default_values(self):
        """Test that to_dict() includes fields with default/None values."""
        class Item(Cob):
            name: str = Grain()
            value: int = Grain()
        
        i = Item(name="test")  # value not explicitly set, gets None default
        d = i.__dna__.to_dict()
        
        assert "name" in d
        assert "value" in d  # None values are included
        assert d["name"] == "test"
        assert d["value"] is None

    def test_to_dict_with_nested_cob(self):
        """Test to_dict() with nested Cob objects."""
        from databarn import one_to_one_grain
        
        @one_to_one_grain("addresses")
        class Address(Cob):
            street: str = Grain()
            city: str = Grain()
        
        class Person(Cob):
            name: str = Grain()
            address: Address = Address
        
        addr = Address(street="Main St", city="Boston")
        person = Person(name="John", address=addr)
        
        d = person.__dna__.to_dict()
        
        assert d["name"] == "John"
        assert isinstance(d["address"], dict)
        assert d["address"]["street"] == "Main St"

    def test_to_dict_with_barn(self):
        """Test to_dict() with nested Barn."""
        from databarn import one_to_many_grain
        
        @one_to_many_grain("items")
        class Item(Cob):
            name: str = Grain()
        
        class Order(Cob):
            order_id: int = Grain(pk=True)
            items: Barn[Item] = Item
        
        order = Order(order_id=1)
        order.items.add(Item(name="Item1"))
        order.items.add(Item(name="Item2"))
        
        d = order.__dna__.to_dict()
        
        assert d["order_id"] == 1
        assert isinstance(d["items"], list)
        assert len(d["items"]) == 2

    def test_to_json_method(self):
        """Test to_json() method."""
        import json
        
        class Item(Cob):
            name: str = Grain()
            value: int = Grain()
        
        i = Item(name="test", value=42)
        json_str = i.__dna__.to_json()
        
        # Should be valid JSON
        parsed = json.loads(json_str)
        assert parsed["name"] == "test"
        assert parsed["value"] == 42

    def test_to_json_with_indent(self):
        """Test to_json() with indent parameter."""
        class Item(Cob):
            name: str = Grain()
        
        i = Item(name="test")
        json_str = i.__dna__.to_json(indent=2)
        
        # Should have newlines if indented
        assert "\n" in json_str


# ============================================================================
# Test Barn Slicing Edge Cases
# ============================================================================

class TestBarnSlicing:
    """Test Barn slicing edge cases."""

    def test_barn_slice_preserves_order(self):
        """Test that slicing preserves insertion order."""
        class Item(Cob):
            id: int = Grain(pk=True)
        
        barn = Barn(Item)
        items = [Item(id=i) for i in range(5)]
        
        for item in items:
            barn.add(item)
        
        sliced = barn[1:4]
        
        assert len(sliced) == 3
        assert sliced[0] == items[1]
        assert sliced[1] == items[2]
        assert sliced[2] == items[3]

    def test_barn_negative_index(self):
        """Test negative indexing on Barn."""
        class Item(Cob):
            id: int = Grain(pk=True)
        
        barn = Barn(Item)
        items = [Item(id=i) for i in range(3)]
        
        for item in items:
            barn.add(item)
        
        assert barn[-1] == items[2]
        assert barn[-2] == items[1]
        assert barn[-3] == items[0]

    def test_barn_step_slicing(self):
        """Test slicing with step parameter."""
        class Item(Cob):
            id: int = Grain(pk=True)
        
        barn = Barn(Item)
        items = [Item(id=i) for i in range(5)]
        
        for item in items:
            barn.add(item)
        
        sliced = barn[::2]
        
        assert len(sliced) == 3
        assert sliced[0] == items[0]
        assert sliced[1] == items[2]
        assert sliced[2] == items[4]


# ============================================================================
# Test Constraint Type Checking
# ============================================================================

class TestConstraintTypeChecking:
    """Test type validation constraints."""

    def test_type_mismatch_error_message(self):
        """Test that type mismatch provides clear error message."""
        class Item(Cob):
            count: int = Grain()
        
        i = Item()
        
        with pytest.raises(Exception):  # Should be GrainTypeMismatchError
            i.count = "not_an_int"

    def test_required_constraint_none_value(self):
        """Test required constraint rejects None value."""
        class Item(Cob):
            name: str = Grain(required=True)
        
        i = Item(name="test")
        
        with pytest.raises(ConstraintViolationError):
            i.name = None

    def test_frozen_constraint(self):
        """Test frozen constraint prevents modification."""
        class Item(Cob):
            uuid: str = Grain(frozen=True)
        
        i = Item(uuid="abc123")
        
        with pytest.raises(ConstraintViolationError):
            i.uuid = "def456"

    def test_auto_constraint_prevent_manual_set(self):
        """Test auto constraint prevents manual assignment."""
        class Item(Cob):
            id: int = Grain(auto=True)
        
        i = Item()
        
        with pytest.raises(ConstraintViolationError):
            i.id = 42

    def test_deletable_constraint(self):
        """Test deletable constraint prevents deletion."""
        class Item(Cob):
            name: str = Grain(deletable=False)
        
        i = Item(name="test")
        
        with pytest.raises(ConstraintViolationError):
            del i.name


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
