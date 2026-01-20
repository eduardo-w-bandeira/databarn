
import pytest
from databarn.barn import Barn
from databarn.cob import Cob
from databarn.grain import Grain
from databarn.exceptions import BarnConsistencyError, DataBarnSyntaxError, ConstraintViolationError

# --- Fixtures & Helper Classes ---

class SimpleCob(Cob):
    name: str = Grain(comparable=True)
    active: bool = Grain(default=True)

class AutoCob(Cob):
    id: int = Grain(auto=True)
    val: str = Grain()

class UniqueCob(Cob):
    uid: int = Grain(unique=True)
    data: str = Grain()

class ComposCob(Cob):
    p1: int = Grain(pk=True)
    p2: int = Grain(pk=True)
    val: str = Grain()

@pytest.fixture
def simple_barn():
    return Barn(SimpleCob)

# --- Tests ---

def test_barn_initialization():
    """Test Barn initialization with valid and invalid models."""
    b = Barn(SimpleCob)
    assert b.model == SimpleCob
    assert len(b) == 0

    # Default model
    b_def = Barn()
    assert b_def.model == Cob

    # Invalid model
    with pytest.raises(BarnConsistencyError):
        Barn(int)

def test_add_cob(simple_barn):
    """Test adding cobs to the barn."""
    c1 = SimpleCob(name="A")
    simple_barn.add(c1)
    
    assert len(simple_barn) == 1
    assert c1 in simple_barn
    assert simple_barn.has_primakey(c1.__dna__.get_keyring())

    # Add wrong type
    class OtherCob(Cob): pass
    c2 = OtherCob()
    with pytest.raises(BarnConsistencyError):
        simple_barn.add(c2)

def test_auto_increment():
    """Test auto-incrementing fields."""
    b = Barn(AutoCob)
    c1 = AutoCob(val="one")
    c2 = AutoCob(val="two")
    
    b.add(c1)
    b.add(c2)
    
    assert c1.id == 1
    assert c2.id == 2

def test_unique_constraint():
    """Test unique constraints."""
    b = Barn(UniqueCob)
    c1 = UniqueCob(uid=10, data="first")
    b.add(c1)
    
    c2 = UniqueCob(uid=10, data="duplicate")
    with pytest.raises(ConstraintViolationError):
        b.add(c2)
        
    c3 = UniqueCob(uid=20, data="ok")
    b.add(c3) # Should pass

def test_primakey_uniqueness():
    """Test primakey uniqueness."""
    class PKCob(Cob):
        pk: int = Grain(pk=True)
        
    b = Barn(PKCob)
    c1 = PKCob(pk=1)
    b.add(c1)
    
    c2 = PKCob(pk=1)
    with pytest.raises(BarnConsistencyError):
        b.add(c2)

    # None primakey
    c3 = PKCob(pk=None) 
    # Depending on implementation, None might be caught before or during add
    # The code says "None is not valid as primakey"
    with pytest.raises(BarnConsistencyError):
        b.add(c3)

def test_composite_primakey():
    """Test composite primakeys."""
    b = Barn(ComposCob)
    c1 = ComposCob(p1=1, p2=1, val="A")
    b.add(c1)
    
    # Same composite key
    c2 = ComposCob(p1=1, p2=1, val="B")
    with pytest.raises(BarnConsistencyError):
        b.add(c2)
        
    # Partial match is OK
    c3 = ComposCob(p1=1, p2=2, val="C")
    b.add(c3)

def test_get_cob(simple_barn):
    """Test retrieving cobs."""
    class PKCob(Cob):
        pk: int = Grain(pk=True)
    
    b = Barn(PKCob)
    c1 = PKCob(pk=100)
    b.add(c1)
    
    # Get by primakey positional
    assert b.get(100) == c1
    
    # Get by primakey kwarg
    assert b.get(pk=100) == c1
    
    # Not found
    assert b.get(999) is None
    
    # Syntax errors
    with pytest.raises(DataBarnSyntaxError):
        b.get() # No args
    with pytest.raises(DataBarnSyntaxError):
        b.get(100, pk=100) # Both

def test_getitem_methods(simple_barn):
    """Test __getitem__ via index and slice."""
    c1 = SimpleCob(name="1")
    c2 = SimpleCob(name="2")
    c3 = SimpleCob(name="3")
    
    simple_barn.add_all(c1, c2, c3)
    
    assert simple_barn[0] == c1
    assert simple_barn[2] == c3
    
    # Slice
    sliced = simple_barn[0:2]
    assert isinstance(sliced, Barn)
    assert len(sliced) == 2
    assert sliced[0] == c1
    assert sliced[1] == c2
    
    with pytest.raises(IndexError):
        _ = simple_barn[10]

def test_remove_cob(simple_barn):
    """Test removing cobs."""
    c1 = SimpleCob(name="A")
    simple_barn.add(c1)
    assert len(simple_barn) == 1
    
    simple_barn.remove(c1)
    assert len(simple_barn) == 0
    assert c1 not in simple_barn

def test_find_and_find_all(simple_barn):
    """Test finding cobs."""
    c1 = SimpleCob(name="Alice", active=True)
    c2 = SimpleCob(name="Bob", active=False)
    c3 = SimpleCob(name="Alice", active=False)
    
    simple_barn.add_all(c1, c2, c3)
    
    # Find first
    f = simple_barn.find(name="Alice")
    assert f == c1
    
    # Find all
    found = simple_barn.find_all(name="Alice")
    assert len(found) == 2
    assert c1 in found
    assert c3 in found
    
    # Find none
    assert simple_barn.find(name="Charlie") is None
    assert len(simple_barn.find_all(name="Charlie")) == 0

    # Find mismatch type (dynamic check skipped for static model test here)
    # Testing logic: if static, it might error if attribute invalid? 
    # Current implementation uses getattr which might raise AttributeError, 
    # OR the logic: if not hasattr -> False (for dynamic). 
    # For static, getattr raises AttributeError. 
    # The `_matches_criteria` catches nothing but does checks.
    # Let's see behavior for non-existent attr on static cob
    with pytest.raises(AttributeError):
        simple_barn.find(non_existent=1)

def test_dynamic_search():
    """Test search behavior with dynamic cobs."""
    class DynCob(Cob): pass
    b = Barn(DynCob)
    
    c1 = DynCob()
    c1.foo = "bar"
    b.add(c1)
    
    c2 = DynCob()
    b.add(c2) # No 'foo'
    
    # Matching
    assert b.find(foo="bar") == c1
    
    # Not matching (c2 doesn't have foo, so safe return False)
    # The code `if self.model.__dna__.dynamic and not hasattr(cob, label): return False`
    # handles this gracefully.
    assert len(b.find_all(foo="bar")) == 1

def test_iteration(simple_barn):
    """Test iteration over barn."""
    c1 = SimpleCob(name="1")
    c2 = SimpleCob(name="2")
    simple_barn.add_all(c1, c2)
    
    lst = [c for c in simple_barn]
    assert lst == [c1, c2]

def test_repr(simple_barn):
    """Test __repr__."""
    assert "0 cobs" in repr(simple_barn)
    simple_barn.add(SimpleCob(name="A"))
    assert "1 cob" in repr(simple_barn)
    simple_barn.add(SimpleCob(name="B"))
    assert "2 cobs" in repr(simple_barn)

