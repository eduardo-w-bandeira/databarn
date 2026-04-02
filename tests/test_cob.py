import pytest

from databarn import Cob, Grain
from databarn.constants import RESERVED_ATTR_NAME
from databarn.exceptions import (
    CobConsistencyError,
    CobConstraintViolationError,
    DataBarnSyntaxError,
    DataBarnViolationError,
    GrainLabelError,
    StaticModelViolationError,
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

    with pytest.raises(StaticModelViolationError):
        Person(name="Alice", age=20)


def test_init_enforces_required_grain() -> None:
    class Person(Cob):
        name: str = Grain(required=True)

    with pytest.raises(CobConstraintViolationError):
        Person()


def test_post_init_is_called_after_assignment() -> None:
    class Line(Cob):
        content: str
        normalized: str

        def __post_init__(self) -> None:
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


def test_reserved_internal_attribute_is_protected() -> None:
    cob = Cob()

    with pytest.raises(DataBarnViolationError):
        setattr(cob, RESERVED_ATTR_NAME, object())

    with pytest.raises(DataBarnViolationError):
        delattr(cob, RESERVED_ATTR_NAME)


def test_setitem_rejects_invalid_identifier_labels() -> None:
    cob = Cob()

    with pytest.raises(GrainLabelError):
        cob["invalid-label"] = 1

    with pytest.raises(GrainLabelError):
        cob[1] = 1  # type: ignore[index]


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


def test_contains_tracks_only_active_values() -> None:
    cob = Cob(name="Alice")
    assert "name" in cob

    del cob["name"]
    assert "name" not in cob


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


def test_eq_with_non_cob_returns_false() -> None:
    class Score(Cob):
        points: int = Grain(comparable=True)

    score = Score(points=1)
    assert (score == object()) is False


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
