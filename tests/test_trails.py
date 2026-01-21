import pytest

from databarn.trails import (
    Unset, UNSET,
    pascal_to_underscore, fo,
    dual_property, dual_method,
    Catalog,
)


def test_unset_repr_and_type():
    assert isinstance(UNSET, Unset)
    assert repr(UNSET) == "<Unset>"


def test_pascal_to_underscore_basic():
    assert pascal_to_underscore("PascalCase") == "pascal_case"
    # Initialisms are split per capital
    assert pascal_to_underscore("HTTPResponseCode") == "h_t_t_p_response_code"
    assert pascal_to_underscore("X") == "x"
    # Mixed with underscore retains and inserts before caps (not first)
    assert pascal_to_underscore("Already_Underscore") == "already__underscore"


def test_fo_compacts_whitespace():
    s = "  Line1\n\tLine2   Line3  "
    assert fo(s) == "Line1 Line2 Line3"


def test_dual_property_class_and_instance():
    class Foo:
        kind = "CLASS"

        def __init__(self):
            self.kind = "INSTANCE"

        @dual_property
        def level(self_or_cls):
            # returns class or instance attribute `kind`
            return getattr(self_or_cls, "kind")

    # Access via class
    assert Foo.level == "CLASS"
    # Access via instance
    assert Foo().level == "INSTANCE"


def test_dual_method_class_and_instance():
    class Bar:
        def __init__(self, prefix="inst"):
            self.prefix = prefix

        @dual_method
        def greet(self_or_cls, name):
            if isinstance(self_or_cls, type):
                return f"class:{name}"
            return f"{self_or_cls.prefix}:{name}"

    assert Bar.greet("bob") == "class:bob"
    assert Bar(prefix="yo").greet("bob") == "yo:bob"


def test_catalog_add_contains_and_order():
    c = Catalog()
    c.add(1)
    c.add(2)
    c.add(2)  # duplicate should be ignored
    assert 1 in c
    assert 2 in c
    assert len(c) == 2
    assert list(c) == [1, 2]
    assert c[0] == 1
    assert c[0:2] == [1, 2]


def test_catalog_unhashable_dicts_and_equality():
    c = Catalog()
    a = {"x": 1}
    b = {"x": 1}
    c.add(a)
    assert a in c
    # Equivalent dict should be considered present, so not added twice
    c.add(b)
    assert len(c) == 1
    # Discard by equal value should remove
    c.discard(b)
    assert len(c) == 0


def test_catalog_remove_and_discard_behavior():
    c = Catalog([1, 2])
    # discard of missing value is silent
    c.discard(3)
    assert len(c) == 2
    # remove of missing value raises
    with pytest.raises(KeyError):
        c.remove(3)


def test_catalog_identity_equals_fallback():
    class WeirdEq:
        def __eq__(self, other):
            raise RuntimeError("boom")

    c = Catalog()
    o1 = WeirdEq()
    o2 = WeirdEq()
    c.add(o1)
    # Membership for the same object should succeed
    assert o1 in c
    # Different object should not be considered contained (id differs)
    assert o2 not in c
    # Adding the same object again stays unique
    c.add(o1)
    assert len(c) == 1
    # Discard removes it
    c.discard(o1)
    assert len(c) == 0


def test_catalog_repr_contains_items():
    c = Catalog([1, 2])
    rep = repr(c)
    assert rep.startswith("Catalog(")
    assert "1" in rep and "2" in rep
