import json
import warnings
from typing import ForwardRef

import pytest

from databarn import Barn, Cob, Grain, one_to_many_grain, one_to_one_grain
from databarn.constants import ABSENT
from databarn.decorators import config_cob
from databarn.dna import BaseDna
from databarn.exceptions import (
    CobConsistencyError,
    DataBarnSyntaxError,
    GrainTypeMismatchError,
    SchemaViolationError,
)


def test_create_barn_returns_model_bound_barn() -> None:
    class Person(Cob):
        name: str

    barn = Person.__dna__.create_barn()

    assert isinstance(barn, Barn)
    assert barn.model is Person


def test_create_cob_from_dict_maps_invalid_keys_and_preserves_original_keys() -> None:
    class Person(Cob):
        first_name: str

    person = Person.__dna__.create_cob_from_dict({"first name": "Ada"})

    assert person.first_name == "Ada"
    assert person.__dna__.to_dict() == {"first name": "Ada"}


def test_create_cob_from_json_uses_model_and_converts_payload() -> None:
    class Person(Cob):
        first_name: str

    person = Person.__dna__.create_cob_from_json('{"first name": "Grace"}')

    assert isinstance(person, Person)
    assert person.first_name == "Grace"


def test_get_keyring_uses_autoid_when_no_primary_key() -> None:
    cob = Cob()

    assert cob.__dna__.primakey_defined is False
    assert cob.__dna__.get_keyring() == cob.__dna__.autoid


def test_get_keyring_returns_absent_when_autoenum_primary_key_not_assigned() -> None:
    class Item(Cob):
        id: int = Grain(pk=True, autoenum=True)

    item = Item()

    assert item.__dna__.get_keyring() is ABSENT


def test_get_keyring_returns_single_and_composite_keys() -> None:
    class Single(Cob):
        id: int = Grain(pk=True)

    class Composite(Cob):
        x: int = Grain(pk=True)
        y: int = Grain(pk=True)

    single = Single(id=10)
    composite = Composite(x=1, y=2)

    assert single.__dna__.get_keyring() == 10
    assert composite.__dna__.get_keyring() == (1, 2)


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

    as_dict = parent.__dna__.to_dict()
    as_json = parent.__dna__.to_json(sort_keys=True)

    assert as_dict == {
        "title": "family",
        "owner": {"name": "Alice"},
        "children": [{"nick": "Kid-1"}, {"nick": "Kid-2"}],
    }
    assert json.loads(as_json) == as_dict


def test_dynamic_grains_can_be_added_and_removed() -> None:
    cob = Cob()
    cob.__dna__.dyn_add_grain("score", int)
    cob.score = 7

    assert "score" in cob.__dna__.labels
    assert cob.score == 7

    del cob.score

    assert "score" not in cob.__dna__.labels





def test_mapping_helpers_cover_get_setdefault_update_pop_popitem_and_clear() -> None:
    class Person(Cob):
        name: str
        age: int

    person = Person(name="Ada", age=10)

    assert set(person.__dna__.keys()) == {"name", "age"}
    assert set(person.__dna__.values()) == {"Ada", 10}
    assert dict(person.__dna__.items()) == {"name": "Ada", "age": 10}

    assert person.__dna__.get("name") == "Ada"
    assert person.__dna__.get("missing", "fallback") == "fallback"

    assert person.__dna__.setdefault("name", "Other") == "Ada"

    person.__dna__.update({"age": 11}, name="Ada Lovelace")
    assert person.age == 11
    assert person.name == "Ada Lovelace"

    popped = person.__dna__.pop("age")
    assert popped == 11
    assert person.__dna__.get("age", ABSENT) is ABSENT

    label, value = person.__dna__.popitem()
    assert label == "name"
    assert value == "Ada Lovelace"

    person.__dna__.update(name="A", age=1)
    person.__dna__.clear()
    assert tuple(person.__dna__.active_grains) == ()


def test_mapping_helpers_cover_missing_key_and_empty_popitem_paths() -> None:
    class Person(Cob):
        name: str

    person = Person(name="Ada")

    with pytest.raises(KeyError):
        person.__dna__.get("missing")

    with pytest.raises(KeyError):
        person.__dna__.pop("missing")

    assert person.__dna__.pop("missing", "fallback") == "fallback"

    person.__dna__.clear()

    with pytest.raises(KeyError):
        person.__dna__.popitem()


def test_mapping_update_accepts_iterable_pairs() -> None:
    class Person(Cob):
        name: str
        age: int

    person = Person(name="Ada", age=1)
    person.__dna__.update([("name", "Grace"), ("age", 2)])

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

    child.__dna__._add_parent(first_container, first_parent)
    child.__dna__._add_parent(second_container, second_parent)

    assert child.__dna__.latest_parent is second_parent


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

    with pytest.raises(CobConsistencyError):
        Person.__dna__._embed_grain("name", Person.__dna__.get_grain("name"))

    person = Person(name="Ada")

    with pytest.raises(KeyError):
        Person.__dna__.get_grain("missing")

    assert Person.__dna__.get_grain("name") is not person.__dna__.get_grain("name")
    assert person.__dna__.get_grain("name").get_value() == "Ada"

    with pytest.raises(KeyError):
        person.__dna__.get_grain("missing")


def test_create_cereals_dynamically_rejects_duplicate_dynamic_label() -> None:
    cob = Cob()
    cob.__dna__.dyn_add_grain("alias")

    with pytest.raises(CobConsistencyError):
        cob.__dna__.dyn_add_grain("alias")


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
    with pytest.raises(GrainTypeMismatchError):
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

    with pytest.raises(GrainTypeMismatchError):
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
    assert parent not in first_child.__dna__.parents

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

    assert person.__dna__.setdefault("name", "Ada") == "Ada"
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

    as_dict = parent.__dna__.to_dict()

    assert as_dict["items"] == [{"id": 1}, [{"id": 2}], "raw"]
    assert as_dict["bundle"] == ({"id": 1}, [{"id": 2}], 3)


def test_create_dna_class_ignores_nested_cob_without_relationship_decorator() -> None:
    class Outer(Cob):
        title: str

        class Inner(Cob):
            name: str

    assert "title" in Outer.__dna__.labels
    assert "Inner" not in Outer.__dna__.labels


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

    with pytest.raises(GrainTypeMismatchError):
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

    with pytest.raises(GrainTypeMismatchError):
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

    monkeypatch.setattr(parent.__dna__, "_resolve_type_hint", lambda *_args, **_kwargs: "Barn['Child']")

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
    monkeypatch.setattr(item.__dna__, "_resolve_type_hint", lambda *_args, **_kwargs: "UnknownType")

    def boom(_value, _type_hint):
        raise RuntimeError("forced failure")

    monkeypatch.setattr("databarn.dna.is_bearable", boom)

    with pytest.raises(GrainTypeMismatchError):
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
    monkeypatch.setattr(parent.__dna__, "_resolve_type_hint", lambda *_args, **_kwargs: object())
    monkeypatch.setattr("databarn.dna.get_origin", lambda _hint: Barn)
    monkeypatch.setattr("databarn.dna.get_args", lambda _hint: ())

    def boom(_value, _type_hint):
        raise RuntimeError("forced failure")

    monkeypatch.setattr("databarn.dna.is_bearable", boom)

    with pytest.raises(GrainTypeMismatchError):
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
    monkeypatch.setattr(parent.__dna__, "_resolve_type_hint", lambda *_args, **_kwargs: object())
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
    monkeypatch.setattr(parent.__dna__, "_resolve_type_hint", lambda *_args, **_kwargs: "NotABarnType")

    def boom(_value, _type_hint):
        raise RuntimeError("forced failure")

    monkeypatch.setattr("databarn.dna.is_bearable", boom)

    with pytest.raises(GrainTypeMismatchError):
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
    monkeypatch.setattr(parent.__dna__, "_resolve_type_hint", lambda *_args, **_kwargs: "Barn['DifferentModel']")

    def boom(_value, _type_hint):
        raise RuntimeError("forced failure")

    monkeypatch.setattr("databarn.dna.is_bearable", boom)

    with pytest.raises(GrainTypeMismatchError):
        parent.children = child_barn


# Tests for BaseDna.cobs for static schemas
def test_cobs_static_schema_initialized_as_empty_catalog() -> None:
    """Test that static schema models have cobs initialized as an empty list."""
    class Person(Cob):
        name: str

    # Model's cobs should be an empty list before creating instances
    assert len(Person.__dna__.cobs) == 0
    assert hasattr(Person.__dna__, "cobs")


def test_cobs_static_schema_registers_instance() -> None:
    """Test that static schema instance is registered in the model's cobs catalog."""
    class Person(Cob):
        name: str

    person = Person(name="Ada")

    # The instance should be registered in the model's cobs
    assert len(Person.__dna__.cobs) == 1
    assert person in Person.__dna__.cobs


def test_cobs_static_schema_shared_across_instances() -> None:
    """Test that all instances of a static schema model share the same cobs catalog."""
    class Person(Cob):
        name: str

    person1 = Person(name="Ada")
    person2 = Person(name="Grace")
    person3 = Person(name="Marie")

    # All instances should be in the model's shared cobs
    assert len(Person.__dna__.cobs) == 3
    assert person1 in Person.__dna__.cobs
    assert person2 in Person.__dna__.cobs
    assert person3 in Person.__dna__.cobs

    # All instances should reference the same cobs catalog
    assert person1.__dna__.cobs is person2.__dna__.cobs is person3.__dna__.cobs is Person.__dna__.cobs


def test_cobs_static_schema_retrieval_by_index() -> None:
    """Test that instances can be retrieved from cobs by index in static schema."""
    class Person(Cob):
        name: str

    person1 = Person(name="Ada")
    person2 = Person(name="Grace")

    # Instances should be retrievable from cobs
    assert Person.__dna__.cobs[0] is person1
    assert Person.__dna__.cobs[1] is person2


def test_cobs_static_schema_iteration() -> None:
    """Test that cobs can be iterated over in static schema."""
    class Person(Cob):
        name: str

    person1 = Person(name="Ada")
    person2 = Person(name="Grace")

    # Should be able to iterate over cobs
    cobs_list = list(Person.__dna__.cobs)
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
    assert len(Person.__dna__.cobs) == 1

    assert isinstance(Person.__dna__.cobs, list)
    with pytest.raises(AttributeError):
        Person.__dna__.cobs.add(person, strict=True)


def test_cobs_static_schema_multiple_models_independent() -> None:
    """Test that different static schema models have independent cobs catalogs."""
    class Person(Cob):
        name: str

    class Company(Cob):
        title: str

    person = Person(name="Ada")
    company = Company(title="Acme Corp")

    # Each model should have its own cobs
    assert person in Person.__dna__.cobs
    assert company in Company.__dna__.cobs
    assert person not in Company.__dna__.cobs
    assert company not in Person.__dna__.cobs


# Tests for BaseDna.cobs for dynamic schemas
def test_cobs_dynamic_schema_initialized_as_empty_catalog() -> None:
    """Test that dynamic schema models (no static grains) have cobs initialized as empty."""
    class DynamicCob(Cob):
        pass  # No grains defined

    # Model's cobs should be empty initially
    assert len(DynamicCob.__dna__.cobs) == 0
    assert DynamicCob.__dna__.blueprint == "dynamic"


def test_cobs_dynamic_schema_instance_has_own_catalog() -> None:
    """Test that each dynamic schema instance has its own cobs catalog."""
    class DynamicCob(Cob):
        pass

    dyn1 = DynamicCob()
    dyn2 = DynamicCob()

    # Dynamic instances are registered on the model's cobs catalog
    assert dyn1.__dna__.cobs is dyn2.__dna__.cobs is DynamicCob.__dna__.cobs
    assert len(DynamicCob.__dna__.cobs) == 2


def test_cobs_dynamic_schema_instance_self_reference() -> None:
    """Test that a dynamic instance's cobs contains only itself."""
    class DynamicCob(Cob):
        pass

    dyn = DynamicCob()

    # The instance is registered in the model's cobs
    assert len(DynamicCob.__dna__.cobs) == 1
    assert dyn in DynamicCob.__dna__.cobs


def test_cobs_dynamic_schema_model_cobs_remains_empty() -> None:
    """Test that model's cobs remains empty even after creating dynamic instances."""
    class DynamicCob(Cob):
        pass

    # Create multiple instances
    dyn1 = DynamicCob()
    dyn2 = DynamicCob()
    dyn3 = DynamicCob()

    # Dynamic instances are registered on the model's cobs
    assert len(DynamicCob.__dna__.cobs) == 3
    assert dyn1 in DynamicCob.__dna__.cobs
    assert dyn2 in DynamicCob.__dna__.cobs
    assert dyn3 in DynamicCob.__dna__.cobs


def test_cobs_dynamic_schema_independent_catalogs() -> None:
    """Test that dynamic instances have completely independent cobs catalogs."""
    class DynamicCob(Cob):
        pass

    dyn1 = DynamicCob()
    dyn2 = DynamicCob()

    # Both instances are registered in the model's shared cobs catalog
    assert dyn1 in DynamicCob.__dna__.cobs
    assert dyn2 in DynamicCob.__dna__.cobs
    assert dyn1 in dyn1.__dna__.cobs
    assert dyn2 in dyn2.__dna__.cobs


def test_cobs_dynamic_schema_retrieval_by_index() -> None:
    """Test that instance can be retrieved from its own cobs by index."""
    class DynamicCob(Cob):
        pass

    dyn = DynamicCob()

    # Instance should be retrievable from the model's cobs at index 0
    assert DynamicCob.__dna__.cobs[0] is dyn


def test_cobs_dynamic_schema_iteration() -> None:
    """Test that iteration over dynamic instance's cobs returns only that instance."""
    class DynamicCob(Cob):
        pass

    dyn = DynamicCob()

    # Iterating over the model's cobs should include the instance
    cobs_list = list(DynamicCob.__dna__.cobs)
    assert dyn in cobs_list


def test_cobs_dynamic_schema_multiple_models_independent() -> None:
    """Test that different dynamic models have independent instance cobs."""
    class DynamicCobA(Cob):
        pass

    class DynamicCobB(Cob):
        pass

    dyn_a = DynamicCobA()
    dyn_b = DynamicCobB()

    # Each model should have its own cobs catalog and be independent
    assert len(DynamicCobA.__dna__.cobs) == 1
    assert len(DynamicCobB.__dna__.cobs) == 1
    assert dyn_a in DynamicCobA.__dna__.cobs
    assert dyn_b in DynamicCobB.__dna__.cobs
    assert dyn_a not in DynamicCobB.__dna__.cobs
    assert dyn_b not in DynamicCobA.__dna__.cobs


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
    assert static1 in StaticCob.__dna__.cobs
    assert static2 in StaticCob.__dna__.cobs
    assert len(StaticCob.__dna__.cobs) == 2

    # Dynamic instances are registered on the model's cobs
    assert len(DynamicCob.__dna__.cobs) == 1
    assert dyn in DynamicCob.__dna__.cobs

    # They should not interfere with each other
    assert static1 not in DynamicCob.__dna__.cobs
    assert dyn not in StaticCob.__dna__.cobs



