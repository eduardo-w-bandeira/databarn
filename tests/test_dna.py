import json

import pytest

from databarn import Barn, Cob, Grain, one_to_many_grain, one_to_one_grain
from databarn.constants import ABSENT
from databarn.exceptions import StaticModelViolationError


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

    cob.__dna__.add_grain_dynamically("score", int, Grain())
    cob.score = 7

    assert "score" in cob.__dna__.labels
    assert cob.score == 7

    del cob.score

    assert "score" not in cob.__dna__.labels


def test_remove_cereals_dynamically_rejects_static_models() -> None:
    class Person(Cob):
        name: str

    person = Person(name="Ada")

    with pytest.raises(StaticModelViolationError):
        person.__dna__._remove_cereals_dynamically("name")


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
    assert tuple(person.__dna__.active_grists) == ()


def test_latest_parent_returns_most_recent_parent() -> None:
    child = Cob()
    first_parent = Cob()
    second_parent = Cob()

    child.__dna__._add_parent(first_parent)
    child.__dna__._add_parent(second_parent)

    assert child.__dna__.latest_parent is second_parent
