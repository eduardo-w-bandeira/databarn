import pytest

from databarn.trails import Catalog, Sentinel, classmethod_only, dual_method, dual_property, fo


def test_sentinel_repr_and_distinct_instances() -> None:
    first = Sentinel("MISSING_ARG")
    second = Sentinel("MISSING_ARG")

    assert repr(first) == "<MISSING_ARG>"
    assert first is not second


def test_fo_collapses_multiline_whitespace() -> None:
    formatted = fo("""
        Hello,
            world!

        This\tis   spaced.
    """)

    assert formatted == "Hello, world! This is spaced."


def test_catalog_preserves_order_and_supports_unhashable_items() -> None:
    first = {"id": 1}
    second = {"id": 2}
    duplicate_first = first

    catalog = Catalog([first, second, duplicate_first])

    assert len(catalog) == 2
    assert list(catalog) == [first, second]
    assert catalog[0] == first
    assert catalog[1:] == [second]
    assert repr(catalog) == f"Catalog({[first, second]!r})"
    assert first in catalog
    assert duplicate_first in catalog


def test_catalog_remove_and_discard_behave_like_an_ordered_set() -> None:
    catalog = Catalog(["a", "b", "c"])
    catalog.remove("b", strict=False)
    assert list(catalog) == ["a", "c"]

    catalog.remove("a")
    assert list(catalog) == ["c"]

    with pytest.raises(KeyError):
        catalog.remove("missing")


def test_dual_property_works_for_class_and_instance_access() -> None:
    class Sample:
        value = 10

        @dual_property
        def doubled(owner):
            return owner.value * 2

    sample = Sample()

    assert Sample.doubled == 20
    assert sample.doubled == 20


def test_dual_method_works_for_class_and_instance_access() -> None:
    class Sample:
        base = 3

        @dual_method
        def compute(owner, offset, scale=1):
            return (owner.base + offset) * scale

    sample = Sample()

    assert Sample.compute(2, scale=4) == 20
    assert sample.compute(2, scale=4) == 20


def test_classmethod_only_allows_class_access() -> None:
    class Sample:
        prefix = "ok"

        @classmethod_only
        def build(cls):
            return f"{cls.prefix}-built"

    sample = Sample()

    assert Sample.build() == "ok-built"

    with pytest.raises(AttributeError):
        sample.build()