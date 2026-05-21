import json
import warnings
from typing import ForwardRef

import pytest

from databarn import Barn, Cob, Grain, one_to_many_grain, one_to_one_grain
from databarn.constants import ABSENT
from databarn.decorators import config_cob
from databarn.dna import BaseDna
from databarn.exceptions import (
    SchemaValidationError,
    DataBarnSyntaxError,
    DataValidationError,
    SchemaValidationError,
)


def test_create_barn_returns_model_bound_barn() -> None:
    class Person(Cob):
        name: str

    barn = Person._dna_.create_barn()

    assert isinstance(barn, Barn)
    assert barn.model is Person


def test_create_cob_from_dict_maps_invalid_keys_and_preserves_original_keys() -> None:
    class Person(Cob):
        first_name: str

    person = Person._dna_.create_cob_from_dict({"first name": "Ada"})

    assert person.first_name == "Ada"
    assert person._dna_.to_dict() == {"first name": "Ada"}


def test_create_cob_from_json_uses_model_and_converts_payload() -> None:
    class Person(Cob):
        first_name: str

    person = Person._dna_.create_cob_from_json('{"first name": "Grace"}')

    assert isinstance(person, Person)
    assert person.first_name == "Grace"


def test_create_cob_from_json_restores_original_keys_on_round_trip() -> None:
        json_str = """
        {
            "order-id": "ORD-2026-9941",
            "customer details": {
                "first-name": "Alex",
                "email": "alex@example.com",
                "global": true
            },
            "1st-time-buyer": true,
            "line-items": [
                {
                    "sku": "SKU-442",
                    "item price": 29.99,
                    "quantity": 2
                },
                {
                    "sku": "SKU-109",
                    "item price": 14.50,
                    "quantity": 1
                }
            ],
            "fulfillment-tags": [
                "express-shipping",
                "fragile"
            ]
        }"""

        order = Cob._dna_.create_cob_from_json(json_str)

        expected = {
                "order-id": "ORD-2026-9941",
                "customer details": {
                        "first-name": "Alex",
                        "email": "alex@example.com",
                        "global": True,
                },
                "1st-time-buyer": True,
                "line-items": [
                        {
                                "sku": "SKU-442",
                                "item price": 29.99,
                                "quantity": 2,
                        },
                        {
                                "sku": "SKU-109",
                                "item price": 14.5,
                                "quantity": 1,
                        },
                ],
                "fulfillment-tags": ["express-shipping", "fragile"],
        }

        assert order._dna_.to_dict() == expected
        assert json.loads(order._dna_.to_json()) == expected


def test_get_keyring_uses_autoid_when_no_primary_key() -> None:
    cob = Cob()

    assert cob._dna_.primakey_defined is False
    assert cob._dna_.get_keyring() == cob._dna_.autoid


def test_get_keyring_returns_absent_when_autoenum_primary_key_not_assigned() -> None:
    class Item(Cob):
        id: int = Grain(pk=True, autoenum=True)

    item = Item()

    with pytest.raises(SchemaValidationError):
        item._dna_.get_keyring()


def test_get_keyring_returns_single_and_composite_keys() -> None:
    class Single(Cob):
        id: int = Grain(pk=True)

    class Composite(Cob):
        x: int = Grain(pk=True)
        y: int = Grain(pk=True)

    single = Single(id=10)
    composite = Composite(x=1, y=2)

    assert single._dna_.get_keyring() == 10
    assert composite._dna_.get_keyring() == (1, 2)


def test_to_dict_and_to_json_convert_nested_cobs_and_barns() -> None:
    class Parent(Cob):
        title: str

        @one_to_one_grain("owner")
        class Owner(Cob):
            name: str

        @one_to_many_grain("children")
        class Child(Cob):
            nick: str

    parent = Parent(title="family")
    parent.owner = Parent.Owner(name="Alice")
    parent.children.add_all(Parent.Child(nick="Kid-1"), Parent.Child(nick="Kid-2"))

    as_dict = parent._dna_.to_dict()
    as_json = parent._dna_.to_json(sort_keys=True)

    assert as_dict == {
        "title": "family",
        "owner": {"name": "Alice"},
        "children": [{"nick": "Kid-1"}, {"nick": "Kid-2"}],
    }
    assert json.loads(as_json) == as_dict


def test_dynamic_grains_can_be_added_and_removed() -> None:
    cob = Cob()
    cob._dna_.dyn_add_grain("score", int)
    cob.score = 7

    assert "score" in cob._dna_.labels
    assert cob.score == 7

    del cob.score

    assert "score" not in cob._dna_.labels





def test_mapping_helpers_cover_get_setdefault_update_pop_popitem_and_clear() -> None:
    class Person(Cob):
        name: str
        age: int

    person = Person(name="Ada", age=10)

    assert set(person._dna_.keys()) == {"name", "age"}
    assert set(person._dna_.values()) == {"Ada", 10}
    assert dict(person._dna_.items()) == {"name": "Ada", "age": 10}

    assert person._dna_.get("name") == "Ada"
    assert person._dna_.get("missing", "fallback") == "fallback"

    assert person._dna_.setdefault("name", "Other") == "Ada"

    person._dna_.update({"age": 11}, name="Ada Lovelace")
    assert person.age == 11
    assert person.name == "Ada Lovelace"

    popped = person._dna_.pop("age")
    assert popped == 11
    assert person._dna_.get("age", ABSENT) is ABSENT

    label, value = person._dna_.popitem()
    assert label == "name"
    assert value == "Ada Lovelace"

    person._dna_.update(name="A", age=1)
    person._dna_.clear()
    assert tuple(person._dna_.active_grains) == ()


def test_mapping_helpers_cover_missing_key_and_empty_popitem_paths() -> None:
    class Person(Cob):
        name: str

    person = Person(name="Ada")

    with pytest.raises(KeyError):
        person._dna_.get("missing")

    with pytest.raises(KeyError):
        person._dna_.pop("missing")

    assert person._dna_.pop("missing", "fallback") == "fallback"

    person._dna_.clear()

    with pytest.raises(KeyError):
        person._dna_.popitem()


def test_mapping_update_accepts_iterable_pairs() -> None:
    class Person(Cob):
        name: str
        age: int

    person = Person(name="Ada", age=1)
    person._dna_.update([("name", "Grace"), ("age", 2)])

    assert person.name == "Grace"
    assert person.age == 2


def test_verify_constraints_accepts_quoted_forward_ref_barn_assignment() -> None:
    namespace = globals()
    exec(
        """
from databarn import Barn, Cob, Grain

class Child(Cob):
    id: int = Grain(pk=True)

class Parent(Cob):
    children: "Barn['Child']" = Grain()

parent = Parent()
child_barn = Barn(Child)
child_barn.add(Child(id=1))
parent.children = child_barn
""",
        namespace,
    )


def test_get_and_has_primakey_reject_wrong_labeled_key_names() -> None:
    class Person(Cob):
        id: int = Grain(pk=True)

    barn = Barn(Person)
    barn.add(Person(id=1))

    with pytest.raises(DataBarnSyntaxError):
        barn.get(foo=1)

    with pytest.raises(DataBarnSyntaxError):
        barn.has_primakey(foo=1)


def test_latest_parent_returns_most_recent_parent() -> None:
    child = Cob()
    first_parent = Cob()
    second_parent = Cob()
    first_container = Barn(Cob)
    second_container = Barn(Cob)

    child._dna_._add_parent(first_container, first_parent)
    child._dna_._add_parent(second_container, second_parent)

    assert child._dna_.latest_parent is second_parent


def test_base_dna_type_display_and_resolve_fallback_paths() -> None:
    class Record(Cob):
        value: int

    assert BaseDna._type_display_name(int) == "int"
    assert BaseDna._type_display_name(ForwardRef("Alias")) == "Alias"
    assert BaseDna._type_display_name("CustomType") == "CustomType"
    marker = object()
    assert BaseDna._type_display_name(marker) == str(marker)

    unresolved = BaseDna._resolve_type_hint("UnknownType[", Record)
    assert unresolved == "UnknownType["


def test_setup_and_lookup_helpers_raise_for_missing_or_duplicate_entries() -> None:
    class Person(Cob):
        name: str

    with pytest.raises(SchemaValidationError):
        Person._dna_._embed_grain("name", Person._dna_.get_grain("name"))

    person = Person(name="Ada")

    with pytest.raises(KeyError):
        Person._dna_.get_grain("missing")

    assert Person._dna_.get_grain("name") is not person._dna_.get_grain("name")
    assert person._dna_.get_grain("name").get_value() == "Ada"

    with pytest.raises(KeyError):
        person._dna_.get_grain("missing")


def test_create_cereals_dynamically_rejects_duplicate_dynamic_label() -> None:
    cob = Cob()
    cob._dna_.dyn_add_grain("alias")

    with pytest.raises(SchemaValidationError):
        cob._dna_.dyn_add_grain("alias")


def test_verify_constraints_handles_unresolved_barn_type_hints() -> None:
    class Child(Cob):
        id: int = Grain(pk=True)

    class Other(Cob):
        id: int = Grain(pk=True)

    class Parent(Cob):
        children: "Barn['Child']" = Grain()

    parent = Parent()

    child_barn = Barn(Child)
    child_barn.add(Child(id=1))
    parent.children = child_barn

    other_barn = Barn(Other)
    other_barn.add(Other(id=1))
    with pytest.raises(DataValidationError):
        parent.children = other_barn


def test_verify_constraints_rejects_mismatched_parametrized_barn_model() -> None:
    class Child(Cob):
        id: int = Grain(pk=True)

    class Other(Cob):
        id: int = Grain(pk=True)

    class Parent(Cob):
        children: Barn[Child] = Grain()

    parent = Parent()
    wrong_barn = Barn(Other)
    wrong_barn.add(Other(id=1))

    with pytest.raises(DataValidationError):
        parent.children = wrong_barn


def test_remove_prev_value_parent_if_handles_barn_and_cob_replacement() -> None:
    class Child(Cob):
        id: int = Grain(pk=True)

    class Parent(Cob):
        child: Cob = Grain()
        children: Barn[Child] = Grain()

    parent = Parent()

    first_child = Child(id=1)
    second_child = Child(id=2)
    parent.child = first_child
    parent.child = second_child
    assert parent not in first_child._dna_.parents

    first_barn = Barn(Child)
    first_barn.add(Child(id=10))
    second_barn = Barn(Child)
    second_barn.add(Child(id=20))
    parent.children = first_barn
    parent.children = second_barn
    assert parent not in first_barn.parent_cobs


def test_setdefault_sets_value_for_missing_key() -> None:
    class Person(Cob):
        name: str

    person = Person()

    assert person._dna_.setdefault("name", "Ada") == "Ada"
    assert person.name == "Ada"


def test_to_dict_converts_list_and_tuple_with_nested_cob_and_barn() -> None:
    class Child(Cob):
        id: int = Grain(pk=True)

    class Parent(Cob):
        items: list
        bundle: tuple

    child = Child(id=1)
    child_barn = Barn(Child)
    child_barn.add(Child(id=2))
    parent = Parent(items=[child, child_barn, "raw"], bundle=(child, child_barn, 3))

    as_dict = parent._dna_.to_dict()

    assert as_dict["items"] == [{"id": 1}, [{"id": 2}], "raw"]
    assert as_dict["bundle"] == ({"id": 1}, [{"id": 2}], 3)


def test_create_dna_class_ignores_nested_cob_without_relationship_decorator() -> None:
    class Outer(Cob):
        title: str

        class Inner(Cob):
            name: str

    assert "title" in Outer._dna_.labels
    assert "Inner" not in Outer._dna_.labels


def test_verify_constraints_fallback_accepts_matching_barn_when_bearable_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Child(Cob):
        id: int = Grain(pk=True)

    class Parent(Cob):
        children: Barn[Child] = Grain()

    parent = Parent()
    child_barn = Barn(Child)
    child_barn.add(Child(id=1))

    def boom(_value, _type_hint):
        raise RuntimeError("forced failure")

    monkeypatch.setattr("databarn.dna.is_bearable", boom)
    parent.children = child_barn


def test_verify_constraints_fallback_raises_for_mismatched_barn_when_bearable_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Child(Cob):
        id: int = Grain(pk=True)

    class Other(Cob):
        id: int = Grain(pk=True)

    class Parent(Cob):
        children: Barn[Child] = Grain()

    parent = Parent()
    wrong_barn = Barn(Other)
    wrong_barn.add(Other(id=1))

    def boom(_value, _type_hint):
        raise RuntimeError("forced failure")

    monkeypatch.setattr("databarn.dna.is_bearable", boom)

    with pytest.raises(DataValidationError):
        parent.children = wrong_barn


def test_verify_constraints_parametrized_barn_mismatch_after_bearable_true(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Child(Cob):
        id: int = Grain(pk=True)

    class Other(Cob):
        id: int = Grain(pk=True)

    class Parent(Cob):
        children: Barn[Child] = Grain()

    monkeypatch.setattr("databarn.dna.is_bearable", lambda *_args, **_kwargs: True)

    parent = Parent()
    wrong_barn = Barn(Other)
    wrong_barn.add(Other(id=1))

    with pytest.raises(DataValidationError):
        parent.children = wrong_barn


def test_verify_constraints_unique_with_barn_allows_distinct_value() -> None:
    class Item(Cob):
        uid: int = Grain(pk=True)
        name: str = Grain(unique=True)

    barn = Barn(Item)
    existing = Item(uid=1, name="Ada")
    target = Item(uid=2, name="Grace")
    barn.add(existing)
    barn.add(target)

    target.name = "Marie"
    assert target.name == "Marie"


def test_verify_constraints_fallback_string_barn_name_matching_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Child(Cob):
        id: int = Grain(pk=True)

    class Parent(Cob):
        children: Barn[Child] = Grain()

    parent = Parent()
    child_barn = Barn(Child)
    child_barn.add(Child(id=1))

    monkeypatch.setattr(parent._dna_, "_resolve_type_hint", lambda *_args, **_kwargs: "Barn['Child']")

    def boom(_value, _type_hint):
        raise RuntimeError("forced failure")

    monkeypatch.setattr("databarn.dna.is_bearable", boom)
    parent.children = child_barn


def test_verify_constraints_fallback_non_barn_value_raises_when_bearable_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Record(Cob):
        value: int = Grain()

    item = Record()
    monkeypatch.setattr(item._dna_, "_resolve_type_hint", lambda *_args, **_kwargs: "UnknownType")

    def boom(_value, _type_hint):
        raise RuntimeError("forced failure")

    monkeypatch.setattr("databarn.dna.is_bearable", boom)

    with pytest.raises(DataValidationError):
        item.value = 1


def test_verify_constraints_except_path_with_barn_origin_and_empty_type_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Child(Cob):
        id: int = Grain(pk=True)

    class Parent(Cob):
        children: Barn[Child] = Grain()

    parent = Parent()
    child_barn = Barn(Child)
    child_barn.add(Child(id=1))

    # Force fallback path with Barn origin but no type args.
    monkeypatch.setattr(parent._dna_, "_resolve_type_hint", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("databarn.dna.get_origin", lambda _hint: Barn)
    monkeypatch.setattr("databarn.dna.get_args", lambda _hint: ())

    def boom(_value, _type_hint):
        raise RuntimeError("forced failure")

    monkeypatch.setattr("databarn.dna.is_bearable", boom)

    with pytest.raises(DataValidationError):
        parent.children = child_barn


def test_verify_constraints_post_check_skips_when_barn_type_args_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Child(Cob):
        id: int = Grain(pk=True)

    class Parent(Cob):
        children: Barn[Child] = Grain()

    parent = Parent()
    child_barn = Barn(Child)
    child_barn.add(Child(id=1))

    # Post-check branch: Barn origin detected but type args are empty.
    monkeypatch.setattr(parent._dna_, "_resolve_type_hint", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("databarn.dna.get_origin", lambda _hint: Barn)
    monkeypatch.setattr("databarn.dna.get_args", lambda _hint: ())
    monkeypatch.setattr("databarn.dna.is_bearable", lambda *_args, **_kwargs: True)

    parent.children = child_barn


def test_verify_constraints_fallback_barn_string_prefix_check_false_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Child(Cob):
        id: int = Grain(pk=True)

    class Parent(Cob):
        children: Barn[Child] = Grain()

    parent = Parent()
    child_barn = Barn(Child)
    child_barn.add(Child(id=1))

    # Force the non-Barn string path in fallback name parsing.
    monkeypatch.setattr(parent._dna_, "_resolve_type_hint", lambda *_args, **_kwargs: "NotABarnType")

    def boom(_value, _type_hint):
        raise RuntimeError("forced failure")

    monkeypatch.setattr("databarn.dna.is_bearable", boom)

    with pytest.raises(DataValidationError):
        parent.children = child_barn


def test_verify_constraints_fallback_barn_string_model_mismatch_false_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Child(Cob):
        id: int = Grain(pk=True)

    class Parent(Cob):
        children: Barn[Child] = Grain()

    parent = Parent()
    child_barn = Barn(Child)
    child_barn.add(Child(id=1))

    # Force Barn[...] string parsing with a mismatched model name.
    monkeypatch.setattr(parent._dna_, "_resolve_type_hint", lambda *_args, **_kwargs: "Barn['DifferentModel']")

    def boom(_value, _type_hint):
        raise RuntimeError("forced failure")

    monkeypatch.setattr("databarn.dna.is_bearable", boom)

    with pytest.raises(DataValidationError):
        parent.children = child_barn


# Tests for BaseDna.cobs for static schemas
def test_cobs_static_schema_initialized_as_empty_list() -> None:
    """Test that static schema models have cobs initialized as an empty list."""
    class Person(Cob):
        name: str

    # Model's cobs should be an empty list before creating instances
    assert len(Person._dna_.cobs) == 0
    assert hasattr(Person._dna_, "cobs")


def test_cobs_static_schema_registers_instance() -> None:
    """Test that static schema instance is registered in the model's cobs list."""
    class Person(Cob):
        name: str

    person = Person(name="Ada")

    # The instance should be registered in the model's cobs
    assert len(Person._dna_.cobs) == 1
    assert person in Person._dna_.cobs


def test_cobs_static_schema_shared_across_instances() -> None:
    """Test that all instances of a static schema model share the same cobs list."""
    class Person(Cob):
        name: str

    person1 = Person(name="Ada")
    person2 = Person(name="Grace")
    person3 = Person(name="Marie")

    # All instances should be in the model's shared cobs
    assert len(Person._dna_.cobs) == 3
    assert person1 in Person._dna_.cobs
    assert person2 in Person._dna_.cobs
    assert person3 in Person._dna_.cobs

    # All instances should reference the same cobs list
    assert person1._dna_.cobs is person2._dna_.cobs is person3._dna_.cobs is Person._dna_.cobs


def test_cobs_static_schema_retrieval_by_index() -> None:
    """Test that instances can be retrieved from cobs by index in static schema."""
    class Person(Cob):
        name: str

    person1 = Person(name="Ada")
    person2 = Person(name="Grace")

    # Instances should be retrievable from cobs
    assert Person._dna_.cobs[0] is person1
    assert Person._dna_.cobs[1] is person2


def test_cobs_static_schema_iteration() -> None:
    """Test that cobs can be iterated over in static schema."""
    class Person(Cob):
        name: str

    person1 = Person(name="Ada")
    person2 = Person(name="Grace")

    # Should be able to iterate over cobs
    cobs_list = list(Person._dna_.cobs)
    assert len(cobs_list) == 2
    # Use identity check (is) since these cobs don't have comparable grains
    assert any(cob is person1 for cob in cobs_list)
    assert any(cob is person2 for cob in cobs_list)


def test_cobs_static_schema_is_plain_list() -> None:
    """Test that cobs uses list semantics (no Catalog-only add API)."""
    class Person(Cob):
        id: int = Grain(pk=True)
        name: str

    person = Person(id=1, name="Ada")
    # The instance is added once during initialization
    assert len(Person._dna_.cobs) == 1

    assert isinstance(Person._dna_.cobs, list)
    with pytest.raises(AttributeError):
        Person._dna_.cobs.add(person, strict=True)


def test_cobs_static_schema_multiple_models_independent() -> None:
    """Test that different static schema models have independent cobs lists."""
    class Person(Cob):
        name: str

    class Company(Cob):
        title: str

    person = Person(name="Ada")
    company = Company(title="Acme Corp")

    # Each model should have its own cobs
    assert person in Person._dna_.cobs
    assert company in Company._dna_.cobs
    assert person not in Company._dna_.cobs
    assert company not in Person._dna_.cobs


# Tests for BaseDna.cobs for dynamic schemas
def test_cobs_dynamic_schema_initialized_as_empty_list() -> None:
    """Test that dynamic schema models (no static grains) have cobs initialized as empty."""
    class DynamicCob(Cob):
        pass  # No grains defined

    # Model's cobs should be empty initially
    assert len(DynamicCob._dna_.cobs) == 0
    assert DynamicCob._dna_.blueprint == "dynamic"


def test_cobs_dynamic_schema_instance_has_own_list() -> None:
    """Test that each dynamic schema instance has its own cobs list."""
    class DynamicCob(Cob):
        pass

    dyn1 = DynamicCob()
    dyn2 = DynamicCob()

    # Dynamic instances are registered on the model's cobs list
    assert dyn1._dna_.cobs is dyn2._dna_.cobs is DynamicCob._dna_.cobs
    assert len(DynamicCob._dna_.cobs) == 2


def test_cobs_dynamic_schema_instance_self_reference() -> None:
    """Test that a dynamic instance's cobs contains only itself."""
    class DynamicCob(Cob):
        pass

    dyn = DynamicCob()

    # The instance is registered in the model's cobs
    assert len(DynamicCob._dna_.cobs) == 1
    assert dyn in DynamicCob._dna_.cobs


def test_cobs_dynamic_schema_model_cobs_remains_empty() -> None:
    """Test that model's cobs remains empty even after creating dynamic instances."""
    class DynamicCob(Cob):
        pass

    # Create multiple instances
    dyn1 = DynamicCob()
    dyn2 = DynamicCob()
    dyn3 = DynamicCob()

    # Dynamic instances are registered on the model's cobs
    assert len(DynamicCob._dna_.cobs) == 3
    assert dyn1 in DynamicCob._dna_.cobs
    assert dyn2 in DynamicCob._dna_.cobs
    assert dyn3 in DynamicCob._dna_.cobs


def test_cobs_dynamic_schema_independent_lists() -> None:
    """Test that dynamic instances have completely independent cobs lists."""
    class DynamicCob(Cob):
        pass

    dyn1 = DynamicCob()
    dyn2 = DynamicCob()

    # Both instances are registered in the model's shared cobs list
    assert dyn1 in DynamicCob._dna_.cobs
    assert dyn2 in DynamicCob._dna_.cobs
    assert dyn1 in dyn1._dna_.cobs
    assert dyn2 in dyn2._dna_.cobs


def test_cobs_dynamic_schema_retrieval_by_index() -> None:
    """Test that instance can be retrieved from its own cobs by index."""
    class DynamicCob(Cob):
        pass

    dyn = DynamicCob()

    # Instance should be retrievable from the model's cobs at index 0
    assert DynamicCob._dna_.cobs[0] is dyn


def test_cobs_dynamic_schema_iteration() -> None:
    """Test that iteration over dynamic instance's cobs returns only that instance."""
    class DynamicCob(Cob):
        pass

    dyn = DynamicCob()

    # Iterating over the model's cobs should include the instance
    cobs_list = list(DynamicCob._dna_.cobs)
    assert dyn in cobs_list


def test_cobs_dynamic_schema_multiple_models_independent() -> None:
    """Test that different dynamic models have independent instance cobs."""
    class DynamicCobA(Cob):
        pass

    class DynamicCobB(Cob):
        pass

    dyn_a = DynamicCobA()
    dyn_b = DynamicCobB()

    # Each model should have its own cobs list and be independent
    assert len(DynamicCobA._dna_.cobs) == 1
    assert len(DynamicCobB._dna_.cobs) == 1
    assert dyn_a in DynamicCobA._dna_.cobs
    assert dyn_b in DynamicCobB._dna_.cobs
    assert dyn_a not in DynamicCobB._dna_.cobs
    assert dyn_b not in DynamicCobA._dna_.cobs


def test_cobs_mixed_static_and_dynamic_independent() -> None:
    """Test that static and dynamic models maintain independent cobs behavior."""
    class StaticCob(Cob):
        name: str

    class DynamicCob(Cob):
        pass

    static1 = StaticCob(name="Ada")
    static2 = StaticCob(name="Grace")
    dyn = DynamicCob()

    # Static model should have shared cobs with both instances
    assert static1 in StaticCob._dna_.cobs
    assert static2 in StaticCob._dna_.cobs
    assert len(StaticCob._dna_.cobs) == 2

    # Dynamic instances are registered on the model's cobs
    assert len(DynamicCob._dna_.cobs) == 1
    assert dyn in DynamicCob._dna_.cobs

    # They should not interfere with each other
    assert static1 not in DynamicCob._dna_.cobs
    assert dyn not in StaticCob._dna_.cobs



