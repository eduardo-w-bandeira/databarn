import pytest

from databarn import Barn, Cob, one_to_many_grain, one_to_one_grain


def test_copy_creates_distinct_instance_with_same_values() -> None:
    class Person(Cob):
        name: str

    person = Person(name="Ada")
    clone = person._dna_.copy()

    assert isinstance(clone, Person)
    assert clone is not person
    assert clone.name == "Ada"

    # Modifying the original must not affect the clone
    person.name = "Changed"
    assert clone.name == "Ada"


def test_copy_preserves_nested_structures_and_is_independent() -> None:
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

    clone = parent._dna_.copy()

    assert isinstance(clone, Parent)
    assert clone.title == "family"
    assert isinstance(clone.owner, Parent.Owner)
    assert [c.nick for c in clone.children] == ["Kid-1", "Kid-2"]

    # Mutating original should not affect clone
    parent.owner.name = "Bob"
    parent.children[0].nick = "Changed"
    assert clone.owner.name == "Alice"
    assert [c.nick for c in clone.children] == ["Kid-1", "Kid-2"]

    # Mutating clone should not affect original
    clone.owner.name = "Eve"
    clone.children[1].nick = "Altered"
    assert parent.owner.name == "Bob"
    assert [c.nick for c in parent.children] == ["Changed", "Kid-2"]


def test_copy_preserves_original_keys_on_round_trip() -> None:
    class Person(Cob):
        first_name: str

    person = Person._dna_.load_dict({"first name": "Ada"})
    clone = person._dna_.copy()

    assert isinstance(clone, Person)
    assert clone.first_name == "Ada"
    assert clone._dna_.to_dict() == {"first name": "Ada"}
