import pytest

from databarn import Cob, Grain, post_init
from databarn.constants import DNA_SYMBOL
from databarn.exceptions import (
    CobConsistencyError,
    CobConstraintViolationError,
    DataBarnSyntaxError,
    DataBarnViolationError,
    GrainLabelError,
    SchemaViolationError,
)


def test_metacob_rejects_reserved_label() -> None:
    with pytest.raises(DataBarnSyntaxError):
        class Invalid(Cob):
            __dna__: int = Grain()


def test_metacob_requires_type_annotation_for_grain() -> None:
    with pytest.raises(DataBarnSyntaxError):
        class Invalid(Cob):
            value = Grain()


def test_init_rejects_positional_args_when_no_grains_exist() -> None:
    with pytest.raises(DataBarnSyntaxError):
        Cob(1)


def test_init_rejects_too_many_positional_args() -> None:
    class Person(Cob):
        name: str

    with pytest.raises(DataBarnSyntaxError):
        Person("Alice", "extra")


def test_init_rejects_duplicate_positional_and_keyword_assignment() -> None:
    class Person(Cob):
        name: str
        age: int

    with pytest.raises(DataBarnSyntaxError):
        Person("Alice", name="Bob", age=20)


def test_static_model_rejects_unknown_grain() -> None:
    class Person(Cob):
        name: str

    with pytest.raises(SchemaViolationError):
        Person(name="Alice", age=20)


def test_init_enforces_required_grain() -> None:
    class Person(Cob):
        name: str = Grain(required=True)

    with pytest.raises(CobConstraintViolationError):
        Person()


def test_init_enforces_primary_key_when_not_autoenum() -> None:
    class Record(Cob):
        rid: int = Grain(pk=True)

    with pytest.raises(CobConstraintViolationError):
        Record()


def test_init_enforces_unique_when_not_autoenum() -> None:
    class Record(Cob):
        code: str = Grain(unique=True)

    with pytest.raises(CobConstraintViolationError):
        Record()


def test_init_applies_default_values_for_unset_grains() -> None:
    class Person(Cob):
        name: str = Grain("Unknown")

    person = Person()
    assert person.name == "Unknown"


def test_post_init_is_called_after_assignment() -> None:
    class Line(Cob):
        content: str
        normalized: str

        @post_init
        def normalize(self) -> None:
            self.normalized = self.content.upper()

    line = Line(content="hello")
    assert line.normalized == "HELLO"


def test_getattribute_raises_for_deleted_grain_attribute() -> None:
    class Person(Cob):
        name: str

    person = Person(name="Alice")
    del person.name

    with pytest.raises(AttributeError):
        _ = person.name


def test_setattr_creates_dynamic_grain_in_dynamic_model() -> None:
    cob = Cob()

    cob.nickname = "Ace"

    assert cob.nickname == "Ace"
    assert "nickname" in cob.__dna__.labels


def test_setattr_rejects_unknown_grain_in_static_model() -> None:
    class Person(Cob):
        name: str

    person = Person(name="Alice")

    with pytest.raises(SchemaViolationError):
        person.age = 30


def test_deleting_unset_declared_grain_raises_attributeerror() -> None:
    class Person(Cob):
        name: str

    person = Person()

    with pytest.raises(AttributeError):
        del person.name

    with pytest.raises(AttributeError):
        del person["name"]

    assert "name" in person.__dna__.labels
    assert tuple(person.__dna__.active_grains) == ()


def test_reserved_internal_attribute_is_protected() -> None:
    cob = Cob()

    with pytest.raises(DataBarnViolationError):
        setattr(cob, DNA_SYMBOL, object())

    with pytest.raises(DataBarnViolationError):
        delattr(cob, DNA_SYMBOL)


def test_setitem_rejects_invalid_identifier_labels() -> None:
    cob = Cob()

    with pytest.raises(GrainLabelError):
        cob["invalid-label"] = 1

    with pytest.raises(GrainLabelError):
        cob[1] = 1  # type: ignore[index]


def test_mapping_syntax_protects_reserved_internal_key() -> None:
    cob = Cob()

    with pytest.raises(DataBarnViolationError):
        cob[DNA_SYMBOL] = object()

    with pytest.raises(GrainLabelError):
        del cob[DNA_SYMBOL]


def test_getitem_returns_grain_value() -> None:
    class Person(Cob):
        name: str

    person = Person(name="Alice")

    assert person["name"] == "Alice"


def test_getitem_raises_keyerror_for_missing_grain() -> None:
    cob = Cob()

    with pytest.raises(KeyError):
        _ = cob["missing"]


def test_setitem_sets_grain_value() -> None:
    class Person(Cob):
        name: str

    person = Person()
    person["name"] = "Alice"

    assert person.name == "Alice"


def test_getitem_rejects_non_grain_attributes() -> None:
    cob = Cob()

    with pytest.raises(DataBarnSyntaxError):
        _ = cob["__class__"]


def test_delitem_rejects_non_grain_attributes() -> None:
    cob = Cob()

    with pytest.raises(DataBarnSyntaxError):
        del cob["__class__"]


def test_delitem_raises_keyerror_for_missing_grain() -> None:
    cob = Cob()

    with pytest.raises(KeyError):
        del cob["missing"]


def test_delattr_enforces_pk_frozen_and_required_constraints() -> None:
    class PkEntry(Cob):
        rid: int = Grain(pk=True)

    class FrozenEntry(Cob):
        token: str = Grain(frozen=True)

    class RequiredEntry(Cob):
        name: str = Grain(required=True)

    class UniqueEntry(Cob):
        code: str = Grain(unique=True)

    with pytest.raises(CobConstraintViolationError):
        del PkEntry(rid=1).rid

    with pytest.raises(CobConstraintViolationError):
        del FrozenEntry(token="x").token

    with pytest.raises(CobConstraintViolationError):
        del RequiredEntry(name="Alice").name

    with pytest.raises(CobConstraintViolationError):
        del UniqueEntry(code="abc").code


def test_delattr_removes_dynamic_grain_definition_when_deleted() -> None:
    cob = Cob(alias="A")

    assert "alias" in cob.__dna__.labels
    del cob.alias

    assert "alias" not in cob.__dna__.labels


def test_delattr_unset_dynamic_grain_raises_attributeerror() -> None:
    cob = Cob()

    cob.__dna__.add_grain("alias")
    assert "alias" in cob.__dna__.labels

    with pytest.raises(AttributeError):
        del cob.alias

    assert "alias" in cob.__dna__.labels


def test_delattr_raises_attributeerror_for_unknown_non_grain_attr() -> None:
    cob = Cob()

    with pytest.raises(AttributeError):
        del cob.unknown


def test_contains_tracks_only_active_values() -> None:
    cob = Cob(name="Alice")
    assert "name" in cob

    del cob["name"]
    assert "name" not in cob


def test_len_tracks_active_grains_only() -> None:
    class Person(Cob):
        name: str
        nickname: str | None = Grain()

    person = Person(name="Alice")

    assert len(person) == 1

    person.nickname = None
    assert len(person) == 2

    del person.name
    assert len(person) == 1


def test_comparison_operators_use_comparable_grains() -> None:
    class Score(Cob):
        points: int = Grain(comparable=True)
        label: str

    high = Score(points=10, label="high")
    low = Score(points=5, label="low")

    assert high == Score(points=10, label="x")
    assert high != low
    assert high > low
    assert high >= low
    assert low < high
    assert low <= high


def test_comparison_operators_false_paths_and_equal_paths() -> None:
    class Score(Cob):
        points: int = Grain(comparable=True)

    left = Score(points=10)
    equal = Score(points=10)
    lower = Score(points=5)
    higher = Score(points=20)

    assert not (left > equal)
    assert not (left > higher)
    assert left >= equal
    assert not (left >= higher)
    assert not (left < equal)
    assert not (left < lower)
    assert left <= equal
    assert not (left <= lower)


def test_eq_with_non_cob_returns_false() -> None:
    class Score(Cob):
        points: int = Grain(comparable=True)

    score = Score(points=1)
    assert (score == object()) is False


def test_ne_delegates_to_eq() -> None:
    class Score(Cob):
        points: int = Grain(comparable=True)

    left = Score(points=1)
    right = Score(points=2)

    assert left != right


def test_comparison_requires_comparable_grain() -> None:
    class Record(Cob):
        value: int

    left = Record(value=1)
    right = Record(value=2)

    with pytest.raises(CobConsistencyError):
        _ = left == right


def test_comparison_rejects_different_cob_models() -> None:
    class Score(Cob):
        points: int = Grain(comparable=True)

    class OtherScore(Cob):
        points: int = Grain(comparable=True)

    left = Score(points=1)
    right = OtherScore(points=1)

    with pytest.raises(CobConsistencyError):
        _ = left == right


def test_eq_returns_true_for_same_instance_without_comparable_grain() -> None:
    class Record(Cob):
        value: int

    item = Record(value=1)

    assert item == item


def test_repr_shows_absent_for_unset_model_grain() -> None:
    class Person(Cob):
        name: str

    person = Person()

    assert repr(person) == "Person(name=<ABSENT>)"
