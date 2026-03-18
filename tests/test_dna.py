
import pytest
from typing import Any
from databarn.cob import Cob
from databarn.grain import Grain
from databarn.exceptions import (
    StaticModelViolationError,
    CobConsistencyError,
    GrainTypeMismatchError,
    CobConstraintViolationError,
)

def test_class_initialization_static():
    """Test static model class setup via dna factory."""
    class StaticModel(Cob):
        name: str = Grain(pk=True)
        age: int = Grain(default=0)
    
    dna_cls = StaticModel.__dna__
    
    assert dna_cls.dynamic is False
    assert "name" in dna_cls.label_grain_map
    assert "age" in dna_cls.label_grain_map
    assert "name" in dna_cls.labels
    assert dna_cls.primakey_defined is True
    assert dna_cls.is_compos_primakey is False
    assert dna_cls.primakey_labels == ("name",)
    assert dna_cls.primakey_len == 1

def test_class_initialization_compos_pk():
    """Test static model with composite primary key."""
    class ComposModel(Cob):
        p1: int = Grain(pk=True)
        p2: int = Grain(pk=True)
    
    dna_cls = ComposModel.__dna__
    assert dna_cls.primakey_defined is True
    assert dna_cls.is_compos_primakey is True
    assert set(dna_cls.primakey_labels) == {"p1", "p2"}
    assert dna_cls.primakey_len == 2

def test_instance_initialization():
    """Test BaseDna instance initialization."""
    class Person(Cob):
        name: str = Grain()
    
    # Create instance
    p = Person(name="Bob")
    dna = p.__dna__
    
    assert dna.cob is p
    assert isinstance(dna.autoid, int)
    assert "name" in dna.label_grist_map
    assert len(dna.grists) == 1
    assert dna.dynamic is False

def test_check_and_get_comparables_error():
    """Test error when no comparables are defined."""
    class NoComp(Cob):
        val: int = Grain()
    
    a = NoComp(val=1)
    b = NoComp(val=2)
    
    # Should fail if we try to compare them (usually comparing cobs invokes this, 
    # but we can call internal method to verify logic)
    with pytest.raises(CobConsistencyError) as exc:
        a.__dna__._check_and_get_comparables(b)
    assert "none of its grains are marked as comparable" in str(exc.value)

def test_dynamic_grains_operations():
    """Test adding and removing grains dynamically."""
    class Dyn(Cob):
        pass
    
    d = Dyn()
    dna = d.__dna__
    
    assert dna.dynamic is True
    
    # Typed grain initialization currently attempts to set None and fails.
    with pytest.raises(GrainTypeMismatchError):
        dna.add_grain_dynamically("score", type=int, grain=Grain())

    # Even when set_value(None) fails, the grain/grist are already embedded.
    assert "score" in dna.label_grain_map
    assert "score" in dna.label_grist_map
    d.score = 10
    assert d.score == 10
    
    # Remove grain
    dna._remove_cereals_dynamically("score")
    assert "score" not in dna.label_grain_map
    assert "score" not in dna.label_grist_map
    
    # Remove non-existent
    with pytest.raises(KeyError):
        dna._remove_cereals_dynamically("missing")

def test_dynamic_operations_on_static_error():
    class LocalStatic(Cob):
        x: int = Grain()
        
    s = LocalStatic(x=1)
    dna = s.__dna__
    
    assert dna.dynamic is False
    
    with pytest.raises(StaticModelViolationError):
        dna.add_grain_dynamically("y", type="str", grain=Grain())
        
    with pytest.raises(StaticModelViolationError):
        dna._remove_cereals_dynamically("x")

def test_get_grain_and_grist():
    """Test get_grain and get_grist methods."""
    class Item(Cob):
        tag: str = Grain()
        
    i = Item(tag="alpha")
    dna = i.__dna__
    
    # Success
    g = dna.get_grain("tag")
    assert g.label == "tag"
    s = dna.get_grist("tag")
    assert s.get_value() == "alpha"
    
    # Defaults
    assert dna.get_grain("missing", default=None) is None
    assert dna.get_grist("missing", default=None) is None
    
    # KeyError
    with pytest.raises(KeyError):
        dna.get_grain("missing")
    with pytest.raises(KeyError):
        dna.get_grist("missing")

def test_items_iterator():
    class Pair(Cob):
        a: int = Grain()
        b: int = Grain()
        
    p = Pair(a=1, b=2)
    items = dict(p.__dna__.items())
    assert items == {"a": 1, "b": 2}

def test_verify_constraints_type():
    class Typed(Cob):
        num: int = Grain()
        
    t = Typed(num=1)
    # Correct type
    t.__dna__._verify_constraints(t.__dna__.get_grist("num"), 100)
    
    # Wrong type
    with pytest.raises(GrainTypeMismatchError):
        t.__dna__._verify_constraints(t.__dna__.get_grist("num"), "string")

def test_verify_constraints_required():
    class Req(Cob):
        needed: int = Grain(required=True)
        
    r = Req(needed=5)
    
    # Current behavior validates type before required.
    with pytest.raises(GrainTypeMismatchError) as exc:
        r.__dna__._verify_constraints(r.__dna__.get_grist("needed"), None)
    assert "defined as <class 'int'>" in str(exc.value)

def test_verify_constraints_frozen():
    class Froz(Cob):
        ice: int = Grain(frozen=True)
        
    f = Froz(ice=10)
    # Initial set is fine (during init). 
    # But now it's set. Trying to set again:
    
    with pytest.raises(CobConstraintViolationError) as exc:
        f.__dna__._verify_constraints(f.__dna__.get_grist("ice"), 20)
    assert "frozen=True" in str(exc.value)

def test_to_dict_recursive():
    """Test to_dict recursively with nested Cobs and Barns."""
    class Child(Cob):
        name: str = Grain()
        
    class Parent(Cob):
        child: Child = Grain()
        children_list: list[Child] = Grain()
        
    c1 = Child(name="C1")
    c2 = Child(name="C2")
    
    p = Parent(child=c1, children_list=[c2])
    
    d = p.__dna__.to_dict()
    assert d["child"]["name"] == "C1"
    assert isinstance(d["children_list"], list)
    assert d["children_list"][0]["name"] == "C2"

def test_keyring():
    class PK(Cob):
        id: int = Grain(pk=True)
    
    x = PK(id=999)
    assert x.__dna__.get_keyring() == 999
    
    class NoPK(Cob):
        val: int = Grain()
        
    y = NoPK(val=1)
    # Should use autoid
    assert y.__dna__.get_keyring() == y.__dna__.autoid
    
    class Compos(Cob):
        a: int = Grain(pk=True)
        b: int = Grain(pk=True)
        
    z = Compos(a=1, b=2)
    assert z.__dna__.get_keyring() == (1, 2)


# Dict-like methods tests
def test_keys_iterator():
    """Test keys() method returns iterator of labels with values."""
    class Product(Cob):
        name: str = Grain()
        price: float = Grain()
        stock: int = Grain()
        
    p = Product(name="Widget", price=9.99)
    keys = list(p.__dna__.keys())
    
    # Only keys with set values are returned.
    assert "name" in keys
    assert "price" in keys
    assert "stock" not in keys
    assert len(keys) == 2


def test_values_iterator():
    """Test values() method returns iterator of values."""
    class Point(Cob):
        x: int = Grain()
        y: int = Grain()
        z: int = Grain()
        
    p = Point(x=1, y=2)
    values = list(p.__dna__.values())
    
    assert 1 in values
    assert 2 in values
    assert len(values) == 2


def test_clear():
    """Test clear() method removes all values from cob."""
    class Counter(Cob):
        count: int = Grain()
        total: int = Grain()
        
    c = Counter(count=5, total=100)
    assert c.__dna__.get_grist("count").attr_exists()
    assert c.__dna__.get_grist("total").attr_exists()
    
    c.__dna__.clear()
    
    # All values should be cleared
    assert not c.__dna__.get_grist("count").attr_exists()
    assert not c.__dna__.get_grist("total").attr_exists()


def test_copy_not_implemented():
    """Test copy() method raises NotImplementedError."""
    class Sample(Cob):
        val: int = Grain()
        
    s = Sample(val=42)
    
    with pytest.raises(NotImplementedError) as exc:
        s.__dna__.copy()
    assert "not implemented" in str(exc.value).lower()


def test_fromkeys():
    """Test fromkeys() creates new cob with specified keys and default value."""
    class Record(Cob):
        a: int = Grain()
        b: int = Grain()
        c: int = Grain()
        
    r = Record(a=1)
    new_cob = r.__dna__.fromkeys(['a', 'b'], value=0)
    
    assert new_cob.a == 0
    assert new_cob.b == 0


def test_get_method():
    """Test get() method retrieves values with optional default."""
    class Config(Cob):
        timeout: int = Grain()
        retries: int = Grain()
        
    cfg = Config(timeout=30)
    
    # Key exists with set value
    assert cfg.__dna__.get("timeout") == 30
    
    # Key exists in the model but has no assigned value.
    with pytest.raises(AttributeError):
        cfg.__dna__.get("retries", default=3)
    with pytest.raises(AttributeError):
        cfg.__dna__.get("retries")
    
    # Key doesn't exist as a grain label
    assert cfg.__dna__.get("missing", default=999) == 999
    
    # Key doesn't exist without default
    with pytest.raises(KeyError) as exc:
        cfg.__dna__.get("missing")
    assert "does not exist" in str(exc.value)


def test_pop_method():
    """Test pop() method removes and returns value."""
    class Queue(Cob):
        first: str = Grain()
        second: str = Grain()
        
    q = Queue(first="A", second="B")
    
    # Pop existing key
    value = q.__dna__.pop("first")
    assert value == "A"
    assert not q.__dna__.get_grist("first").attr_exists()
    
    # Pop non-existing key with default
    assert q.__dna__.pop("third", default="C") == "C"
    
    # Pop non-existing key without default
    with pytest.raises(KeyError) as exc:
        q.__dna__.pop("missing")
    assert "does not exist" in str(exc.value)


def test_popitem_method():
    """Test popitem() removes and returns last item."""
    class Stack(Cob):
        item1: str
        item2: str
        item3: str = Grain()
        
    s = Stack(item1="X", item2="Y", item3="Z")
    
    # Pop last item (item3 is last)
    key, value = s.__dna__.popitem()
    assert key == "item3"
    assert value == "Z"
    assert not s.__dna__.get_grist("item3").attr_exists()
    
    # Pop second to last item
    key, value = s.__dna__.popitem()
    assert key == "item2"
    assert value == "Y"
    
    # Pop from empty cob
    s.__dna__.clear()
    with pytest.raises(KeyError) as exc:
        s.__dna__.popitem()
    assert "is empty" in str(exc.value)


def test_setdefault_method():
    """Test setdefault() sets value if key doesn't exist as a grain label."""
    class Settings(Cob):
        theme: str = Grain()
        
    s = Settings(theme="dark")
    
    # Key exists with user-set value - should return existing value
    result = s.__dna__.setdefault("theme", "light")
    assert result == "dark"
    assert s.theme == "dark"
    
    # Key doesn't exist as grain label - should set dynamically and return default
    # Note: This only works for dynamic models (model with no defined grains)
    class DynSettings(Cob):
        pass
    
    ds = DynSettings()
    result = ds.__dna__.setdefault("mode", "autoenum")
    assert result == "autoenum"
    assert ds.mode == "autoenum"


def test_update_method_with_dict():
    """Test update() method with dictionary argument."""
    class Profile(Cob):
        name: str = Grain()
        age: int = Grain()
        city: str = Grain()
        
    p = Profile(name="Alice")
    
    p.__dna__.update({"age": 25, "city": "NYC"})
    
    assert p.name == "Alice"
    assert p.age == 25
    assert p.city == "NYC"


def test_update_method_with_kwargs():
    """Test update() method with keyword arguments."""
    class User(Cob):
        username: str = Grain()
        email: str = Grain()
        active: bool = Grain()
        
    u = User(username="bob")
    
    u.__dna__.update(email="bob@example.com", active=True)
    
    assert u.username == "bob"
    assert u.email == "bob@example.com"
    assert u.active is True


def test_update_method_with_both():
    """Test update() method with both dict and kwargs."""
    class Data(Cob):
        a: int = Grain()
        b: int = Grain()
        c: int = Grain()
        
    d = Data(a=1)
    
    d.__dna__.update({"b": 2}, c=3)
    
    assert d.a == 1
    assert d.b == 2
    assert d.c == 3


def test_update_method_with_iterable():
    """Test update() method with iterable of key-value pairs."""
    class Mapping(Cob):
        x: int = Grain()
        y: int = Grain()
        
    m = Mapping()
    
    m.__dna__.update([("x", 10), ("y", 20)])
    
    assert m.x == 10
    assert m.y == 20

