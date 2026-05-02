import json
from typing import ForwardRef

import pytest

from databarn import Barn, Cob, Grain, one_to_many_grain, one_to_one_grain
from databarn.constants import ABSENT
from databarn.dna import BaseDna
from databarn.exceptions import (
    CobConsistencyError,
    DataBarnSyntaxError,
    GrainTypeMismatchError,
    SchemeViolationError,
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

    cob.__dna__.add_grain("score", int, Grain())
    cob.score = 7

    assert "score" in cob.__dna__.labels
    assert cob.score == 7

    del cob.score

    assert "score" not in cob.__dna__.labels


def test_remove_grain_rejects_static_models() -> None:
    class Person(Cob):
        name: str

    person = Person(name="Ada")

    with pytest.raises(SchemeViolationError):
        person.__dna__._remove_grain("name")


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

    child.__dna__._add_parent(first_parent)
    child.__dna__._add_parent(second_parent)

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


def test_create_and_embed_grain_rejects_foreign_and_duplicate_grains() -> None:
    class Person(Cob):
        name: str

    class Car(Cob):
        model: str

    person = Person(name="Ada")
    foreign_grain = Car.__dna__.get_grain("model")

    with pytest.raises(CobConsistencyError):
        person.__dna__.add_grain("model", grain=foreign_grain)

    with pytest.raises(CobConsistencyError):
        person.__dna__.add_grain("model", grain=Person.__dna__.get_grain("name"))


def test_create_cereals_dynamically_rejects_duplicate_dynamic_label() -> None:
    cob = Cob()
    cob.__dna__.add_grain("alias")

    with pytest.raises(CobConsistencyError):
        cob.__dna__.add_grain("alias")


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
