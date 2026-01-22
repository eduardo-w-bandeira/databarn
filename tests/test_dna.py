
import pytest
from typing import Any
from databarn.cob import Cob
from databarn.grain import Grain
from databarn.exceptions import (
    StaticModelViolationError,
    CobConsistencyError,
    GrainTypeMismatchError,
    ConstraintViolationError,
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
    assert "name" in dna.label_seed_map
    assert len(dna.seeds) == 1
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
    
    # Add grain
    g = dna.add_grain_dynamically("score", type=int)
    assert "score" in dna.label_grain_map
    assert "score" in dna.label_seed_map
    
    # Remove grain
    dna.remove_grain_dynamically("score")
    assert "score" not in dna.label_grain_map
    assert "score" not in dna.label_seed_map
    
    # Remove non-existent
    with pytest.raises(KeyError):
        dna.remove_grain_dynamically("missing")

def test_dynamic_operations_on_static_error():
    class LocalStatic(Cob):
        x: int = Grain()
        
    s = LocalStatic(x=1)
    dna = s.__dna__
    
    assert dna.dynamic is False
    
    with pytest.raises(StaticModelViolationError):
        dna.add_grain_dynamically("y")
        
    with pytest.raises(StaticModelViolationError):
        dna.remove_grain_dynamically("x")

def test_get_grain_and_seed():
    """Test get_grain and get_seed methods."""
    class Item(Cob):
        tag: str = Grain()
        
    i = Item(tag="alpha")
    dna = i.__dna__
    
    # Success
    g = dna.get_grain("tag")
    assert g.label == "tag"
    s = dna.get_seed("tag")
    assert s.get_value() == "alpha"
    
    # Defaults
    assert dna.get_grain("missing", default=None) is None
    assert dna.get_seed("missing", default=None) is None
    
    # KeyError
    with pytest.raises(KeyError):
        dna.get_grain("missing")
    with pytest.raises(KeyError):
        dna.get_seed("missing")

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
    t.__dna__._verify_constraints(t.__dna__.get_seed("num"), 100)
    
    # Wrong type
    with pytest.raises(GrainTypeMismatchError):
        t.__dna__._verify_constraints(t.__dna__.get_seed("num"), "string")

def test_verify_constraints_required():
    class Req(Cob):
        needed: int = Grain(required=True)
        
    r = Req(needed=5)
    
    # Cannot set to None if required
    with pytest.raises(ConstraintViolationError) as exc:
        r.__dna__._verify_constraints(r.__dna__.get_seed("needed"), None)
    assert "required=True" in str(exc.value)

def test_verify_constraints_frozen():
    class Froz(Cob):
        ice: int = Grain(frozen=True)
        
    f = Froz(ice=10)
    # Initial set is fine (during init). 
    # But now it's set. Trying to set again:
    
    with pytest.raises(ConstraintViolationError) as exc:
        f.__dna__._verify_constraints(f.__dna__.get_seed("ice"), 20)
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

