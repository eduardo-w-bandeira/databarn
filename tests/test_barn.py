from typing import Any

import pytest
from beartype.roar import BeartypeCallHintParamViolation

from databarn import Barn, Cob, Grain
from databarn.exceptions import (
    BarnConstraintViolationError,
    CobConstraintViolationError,
    DataBarnViolationError,
    DataBarnSyntaxError,
)


def test_add_rejects_cob_of_different_model() -> None:
    class Person(Cob):
        id: int = Grain(pk=True)

    class Animal(Cob):
        id: int = Grain(pk=True)

    barn = Barn(Person)

    with pytest.raises(BarnConstraintViolationError):
        barn.add(Animal(id=1))


def test_add_assigns_autoenum_primary_key_in_sequence() -> None:
    class Line(Cob):
        id: int = Grain(pk=True, autoenum=True)
        text: str

    barn = Barn(Line)
    first = Line(text="a")
    second = Line(text="b")

    barn.add(first).add(second)

    assert first.id == 1
    assert second.id == 2
    assert barn.get(1) is first
    assert barn.get(2) is second


def test_add_rejects_duplicate_primary_key() -> None:
    class Person(Cob):
        id: int = Grain(pk=True)

    barn = Barn(Person)
    barn.add(Person(id=1))

    with pytest.raises(BarnConstraintViolationError):
        barn.add(Person(id=1))


def test_add_rejects_missing_autoenum_primary_key_before_assignment() -> None:
    class Event(Cob):
        id: int = Grain(pk=True, autoenum=True)

    barn = Barn(Event)
    event = Event()

    # add() performs autoenum assignment first, so validate via the private check.
    with pytest.raises(BarnConstraintViolationError):
        barn._validate_keyring(event)


def test_add_rejects_duplicate_unique_grain_value() -> None:
    class User(Cob):
        id: int = Grain(pk=True)
        email: str = Grain(unique=True)

    barn = Barn(User)
    barn.add(User(id=1, email="a@example.com"))

    with pytest.raises(BarnConstraintViolationError):
        barn.add(User(id=2, email="a@example.com"))


def test_add_accepts_none_primary_key_values() -> None:
    class Person(Cob):
        id: int | None = Grain(pk=True)
        name: str

    barn = Barn(Person)
    person = Person(id=None, name="Ada")

    barn.add(person)

    assert barn.get(None) is person
    assert barn.get(id=None) is person
    assert barn.has_primakey(None) is True
    assert barn.has_primakey(id=None) is True


def test_add_rejects_duplicate_none_unique_values() -> None:
    class User(Cob):
        id: int = Grain(pk=True)
        email: str | None = Grain(unique=True)

    barn = Barn(User)
    barn.add(User(id=1, email=None))

    with pytest.raises(BarnConstraintViolationError):
        barn.add(User(id=2, email=None))


def test_add_all_and_append_insert_cobs() -> None:
    class Person(Cob):
        id: int = Grain(pk=True)

    barn = Barn(Person)
    p1 = Person(id=1)
    p2 = Person(id=2)
    p3 = Person(id=3)

    out = barn.add_all(p1, p2)
    ret = barn.append(p3)

    assert out is barn
    assert ret is None
    assert list(barn) == [p1, p2, p3]


def test_get_keyring_requires_valid_input_patterns() -> None:
    class Person(Cob):
        id: int = Grain(pk=True)

    barn = Barn(Person)

    with pytest.raises(DataBarnSyntaxError):
        barn._get_keyring()

    with pytest.raises(DataBarnSyntaxError):
        barn._get_keyring(1, id=1)

    with pytest.raises(DataBarnSyntaxError):
        barn._get_keyring(1, 2)


def test_get_and_has_primakey_support_labeled_keys_for_static_model() -> None:
    class Person(Cob):
        id: int = Grain(pk=True)
        name: str

    barn = Barn(Person)
    person = Person(id=7, name="Ada")
    barn.add(person)

    assert barn.get(id=7) is person
    assert barn.has_primakey(id=7) is True
    assert barn.has_primakey(id=9) is False


def test_get_rejects_labeled_keys_for_dynamic_model() -> None:
    barn = Barn(Cob)
    barn.add(Cob(id=1))

    with pytest.raises(DataBarnSyntaxError):
        barn.get(id=1)


def test_remove_deletes_stored_cob_and_updates_membership() -> None:
    class Person(Cob):
        id: int = Grain(pk=True)

    barn = Barn(Person)
    person = Person(id=1)
    barn.add(person)

    assert barn in person.__dna__.barns
    barn.remove(person)

    assert len(barn) == 0
    assert barn not in person.__dna__.barns


def test_remove_uses_stored_cob_for_equal_key_instance() -> None:
    class Person(Cob):
        id: int = Grain(pk=True)

    barn = Barn(Person)
    stored = Person(id=1)
    equivalent = Person(id=1)

    barn.add(stored)
    barn.remove(equivalent)

    assert len(barn) == 0
    assert barn not in stored.__dna__.barns


def test_find_and_find_all_filter_by_attributes() -> None:
    class Person(Cob):
        id: int = Grain(pk=True)
        city: str

    p1 = Person(id=1, city="A")
    p2 = Person(id=2, city="B")
    p3 = Person(id=3, city="A")

    barn = Barn(Person).add_all(p1, p2, p3)

    assert barn.find(city="A") is p1
    filtered = barn.find_all(city="A")

    assert isinstance(filtered, Barn)
    assert list(filtered) == [p1, p3]


def test_find_and_find_all_skip_deleted_attributes() -> None:
    class Person(Cob):
        id: int = Grain(pk=True)
        age: int

    person = Person(id=1, age=10)
    del person.age

    barn = Barn(Person).add(person)

    assert barn.find(age=10) is None
    assert list(barn.find_all(age=10)) == []


def test_collection_protocols_len_repr_contains_getitem_slice_and_iter() -> None:
    class Person(Cob):
        id: int = Grain(pk=True)

    p1 = Person(id=1)
    p2 = Person(id=2)
    p3 = Person(id=3)
    barn = Barn(Person).add_all(p1, p2, p3)

    assert len(barn) == 3
    assert repr(Barn(Person)) == "Barn(0 cobs)"
    assert repr(Barn(Person).add(Person(id=99))) == "Barn(1 cob)"
    assert p2 in barn
    assert barn[0] is p1

    sliced = barn[1:]
    assert isinstance(sliced, Barn)
    assert list(sliced) == [p2, p3]
    assert list(iter(barn)) == [p1, p2, p3]


def test_getitem_raises_indexerror_for_out_of_range_index() -> None:
    class Person(Cob):
        id: int = Grain(pk=True)

    barn = Barn(Person).add(Person(id=1))

    with pytest.raises(IndexError):
        _ = barn[5]


def test_parent_cob_propagates_to_children_on_add_and_remove() -> None:
    class Child(Cob):
        id: int = Grain(pk=True)

    parent = Cob()
    c1 = Child(id=1)
    c2 = Child(id=2)
    barn = Barn(Child).add(c1)

    barn._add_parent_cob(parent)

    assert parent in barn.parent_cobs
    assert c1.__dna__.latest_parent is parent

    barn.add(c2)
    assert c2.__dna__.latest_parent is parent

    barn._remove_parent_cob(parent)

    assert parent not in barn.parent_cobs
    assert c1.__dna__.latest_parent is None
    assert c2.__dna__.latest_parent is None


def test_dynamic_uniqueness_checks_skip_missing_grists_in_other_cobs() -> None:
    barn = Barn(Cob)

    stored = Cob(name="stored")
    barn.add(stored)

    candidate = Cob()
    candidate.__dna__.add_grain_dynamically("email", str, Grain(unique=True))
    candidate.email = "a@example.com"

    # _check_uniqueness_by_cob() should skip stored dynamic cobs that do not have this grist.
    assert barn._check_uniqueness_by_cob(candidate) is True

    barn.add(candidate)
    candidate.email = "b@example.com"
    assert candidate.email == "b@example.com"


def test_get_keyring_supports_labeled_composite_primary_keys() -> None:
    class Edge(Cob):
        left: int = Grain(pk=True)
        right: int = Grain(pk=True)

    barn = Barn(Edge)
    edge = Edge(left=1, right=2)
    barn.add(edge)

    assert barn.get(left=1, right=2) is edge
    assert barn.has_primakey(left=1, right=2) is True


def test_find_and_matches_criteria_return_false_for_missing_dynamic_grain() -> None:
    barn = Barn(Cob)
    item = Cob(name="Ada")
    barn.add(item)

    assert barn.find(email="a@example.com") is None
    assert list(barn.find_all(email="a@example.com")) == []


def test_contains_returns_false_for_non_stored_instance() -> None:
    class Person(Cob):
        id: int = Grain(pk=True)

    barn = Barn(Person)
    barn.add(Person(id=1))

    assert Person(id=2) not in barn


def test_uniqueness_invariant_errors_for_static_model_missing_grist() -> None:
    class User(Cob):
        id: int = Grain(pk=True)
        email: str = Grain(unique=True)

    barn = Barn(User)
    stored = User(id=1, email="a@example.com")
    barn.add(stored)

    candidate = User(id=2, email="b@example.com")

    # Synthetic invariant-break: static models should always have this grist.
    original_get_grist = stored.__dna__.get_grist
    stored.__dna__.get_grist = lambda label, default=None: None if label == "email" else original_get_grist(label, default)  # type: ignore[method-assign]

    with pytest.raises(DataBarnViolationError):
        barn._check_uniqueness_by_cob(candidate)


def test_uniqueness_by_value_invariant_error_for_static_model_missing_grist() -> None:
    class User(Cob):
        id: int = Grain(pk=True)
        email: str = Grain(unique=True)

    barn = Barn(User)
    stored = User(id=1, email="a@example.com")
    barn.add(stored)

    # Same invariant-break for the value-based uniqueness path.
    original_get_grist = stored.__dna__.get_grist
    stored.__dna__.get_grist = lambda label, default=None: None if label == "email" else original_get_grist(label, default)  # type: ignore[method-assign]

    with pytest.raises(DataBarnViolationError):
        barn._check_uniqueness_by_value(User.__dna__.get_grain("email"), "x@example.com")


def test_get_keyring_labeled_count_guard_via_monkeypatched_primakey_len(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class User(Cob):
        id: int = Grain(pk=True)

    barn = Barn(User)
    # Defensive branch: force an inconsistent primakey_len to hit count guard.
    monkeypatch.setattr(User.__dna__, "primakey_len", 2, raising=False)

    with pytest.raises(DataBarnSyntaxError):
        barn.get(id=1)


def test_getitem_rejects_non_int_and_non_slice_via_beartype() -> None:
    class User(Cob):
        id: int = Grain(pk=True)

    class IntLike:
        def __index__(self) -> int:
            return 0

    barn = Barn(User).add(User(id=1))

    # Beartype blocks invalid index types before Barn.__getitem__ internal guards.
    with pytest.raises(BeartypeCallHintParamViolation):
        _ = barn[IntLike()]


def test_check_uniqueness_by_value_raises_for_duplicate_value() -> None:
    class User(Cob):
        id: int = Grain(pk=True)
        email: str = Grain(unique=True)

    barn = Barn(User)
    first = User(id=1, email="a@example.com")
    second = User(id=2, email="b@example.com")
    barn.add(first)
    barn.add(second)

    with pytest.raises(CobConstraintViolationError):
        barn._check_uniqueness_by_value(User.__dna__.get_grain("email"), "a@example.com")
