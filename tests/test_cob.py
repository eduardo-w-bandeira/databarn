
import pytest
from databarn.cob import Cob
from databarn.grain import Grain
from databarn.exceptions import StaticModelViolationError, InvalidGrainLabelError, DataBarnSyntaxError

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
    # Order depends on definition order for seeds
    assert repr(item) == "Item(name='Box', id=123)"
