
import pytest
from databarn.cob import Cob
from databarn.grain import Grain
from databarn.exceptions import StaticModelViolationError, InvalidGrainLabelError, DataBarnSyntaxError, CobConstraintViolationError

def test_cob_dynamic_creation():
    """Test creating a dynamic Cob and adding grains."""
    class DynamicCob(Cob):
        pass

    cob = DynamicCob()
    assert cob.__dna__.dynamic is True

    # Test __setattr__
    cob.name = "Test"
    assert "name" in cob
    assert cob.name == "Test"

    # Test __setitem__
    cob["age"] = 30
    assert "age" in cob
    assert cob.age == 30
    assert cob["age"] == 30

def test_cob_static_violation():
    """Test that a static Cob does not allow new grains."""
    class StaticModel(Cob):
        name: str = Grain()

    cob = StaticModel(name="Static")
    assert cob.__dna__.dynamic is False

    # Test __setattr__ does not allow new attribute in static model
    with pytest.raises(StaticModelViolationError):
        cob.new_attr = "Not Allowed"

    # Test __setitem__ violation (stricter)
    with pytest.raises(StaticModelViolationError):
        cob["new_attr_2"] = "Error"


def test_cob_static_missing_type_annotation():
    """Static Cob definition must annotate each Grain."""
    with pytest.raises(DataBarnSyntaxError):
        class InvalidStaticModel(Cob):
            valid_grain_name: int = 3 # Valid
            valid_grain_name2: int = Grain()  # Valid
            invalid_grain_name = Grain()

def test_cob_dict_access():
    """Test dictionary-like access methods."""
    class Person(Cob):
        pass
    
    p = Person()
    p["name"] = "Alice"
    
    # __getitem__
    assert p["name"] == "Alice"
    
    # __contains__
    assert "name" in p
    assert "age" not in p
    
    # __delitem__
    del p["name"]
    assert "name" not in p
    
    # invalid key
    with pytest.raises(KeyError):
        _ = p["non_existent"]
    
    # invalid identifier
    with pytest.raises(InvalidGrainLabelError):
        p["invalid-identifier"] = 1

def test_cob_comparisons():
    """Test comparison operators based on comparable grains."""
    class Score(Cob):
        value: int = Grain(comparable=True)
        ignored: int = Grain(comparable=False, default=0)

    s1 = Score(value=10, ignored=1)
    s2 = Score(value=20, ignored=2)
    s3 = Score(value=10, ignored=99)
    s4 = Score(value=10, ignored=1)

    # Equality (ignores non-comparable grains)
    assert s1 == s3
    assert s1 == s4
    assert s1 != s2

    # Less than
    assert s1 < s2
    assert not (s2 < s1)

    # Greater than
    assert s2 > s1
    assert not (s1 > s2)

    # LE / GE
    assert s1 <= s3
    assert s1 >= s3
    assert s1 <= s2
    assert s2 >= s1

    # Identity equality
    assert s1 == s1

def test_cob_initialization():
    """Test initialization with args and kwargs."""
    class Point(Cob):
        x: int
        y: int

    # Keyword init
    p1 = Point(x=1, y=2)
    assert p1.x == 1
    assert p1.y == 2

    # Positional init
    p2 = Point(10, 20)
    assert p2.x == 10
    assert p2.y == 20

    # Mixed (not allowed if positional covers keywords, check logic)
    # The logic says: cannot assign value to grain ... both positionally and as keyword
    with pytest.raises(DataBarnSyntaxError):
        Point(10, x=5)

    # Too many args
    with pytest.raises(DataBarnSyntaxError):
        Point(1, 2, 3)

def test_cob_repr():
    class Item(Cob):
        name: str = Grain()
        id: int = Grain()
    
    item = Item(name="Box", id=123)
    # Order depends on definition order for grists
    assert repr(item) == "Item(name='Box', id=123)"

def test_cob_attribute_deletion():
    """Test deletion of Cob attributes using del operator."""
    
    # Test deletion in dynamic Cob
    class DynamicCob(Cob):
        pass
    
    dcob = DynamicCob()
    dcob.name = "Alice"
    dcob.age = 30
    
    assert hasattr(dcob, "name")
    assert dcob.name == "Alice"
    
    # Delete the attribute
    del dcob.name
    
    # Verify it's deleted
    assert not hasattr(dcob, "name")
    assert "name" not in dcob
    
    with pytest.raises(AttributeError):
        _ = dcob.name
    
    # Age should still be there
    assert dcob.age == 30
    
    # Test deletion in static Cob
    class StaticCob(Cob):
        title: str
        count: int = Grain(default=0)
    
    scob = StaticCob(title="Document", count=5)
    
    assert hasattr(scob, "title")
    assert scob.title == "Document"
    
    # Delete the attribute
    del scob.title
    
    # Verify it's deleted
    assert not hasattr(scob, "title")
    with pytest.raises(AttributeError):
        _ = scob.title
    
    # Count should still be accessible
    assert scob.count == 5
    
    # Deletion constraints are currently based on pk/frozen/required.
    # Test that deleting a primary key raises an error
    class WithPK(Cob):
        id: int = Grain(pk=True)
        name: str = Grain()

    wpk = WithPK(id=1, name="Test")

    with pytest.raises(CobConstraintViolationError):
        del wpk.id

    # Test that deleting a frozen grain raises an error
    class WithFrozen(Cob):
        immutable: str = Grain(frozen=True)
        mutable: str = Grain()

    wf = WithFrozen(immutable="Frozen", mutable="Mutable")

    with pytest.raises(CobConstraintViolationError):
        del wf.immutable

    # Test that deleting a required grain raises an error
    class WithRequired(Cob):
        required_field: str = Grain(required=True)
        optional_field: str = Grain()

    wr = WithRequired(required_field="Required", optional_field="Optional")

    with pytest.raises(CobConstraintViolationError):
        del wr.required_field
