import pytest

from databarn import Cob, Grain
from databarn.exceptions import CobConsistencyError, CobConstraintViolationError


def test_grain_rejects_default_and_factory() -> None:
    with pytest.raises(CobConsistencyError):
        Grain(default=1, factory=lambda: 2)


def test_grain_metadata_helpers_and_repr() -> None:
    class Owner(Cob):
        title: str

    grain = Grain(default="Ada", pk=True, required=True, frozen=True, unique=True,
                  comparable=True, key="display_name", info={"source": "manual"})

    grain._set_parent_model_metadata(parent_model=Owner, label="title", type=str)
    grain._set_child_model(Owner, is_child_barn=True)
    grain.set_key("full_name")

    assert grain.label == "title"
    assert grain.type is str
    assert grain.parent_model is Owner
    assert grain.child_model is Owner
    assert grain.is_child_barn is True
    assert grain.key == "full_name"
    assert grain.info.source == "manual"

    grain_repr = repr(grain)
    assert grain_repr.startswith("Grain<")
    assert "label='title'" in grain_repr
    assert "key='full_name'" in grain_repr


def test_grist_value_access_and_force_set_value() -> None:
    class Person(Cob):
        name: str
        age: int = Grain(frozen=True)

    person = Person(name="Ada", age=10)
    name_grist = person.__dna__.get_grist("name")
    age_grist = person.__dna__.get_grist("age")

    assert name_grist.label == "name"
    assert name_grist.pk is False
    assert "label" in dir(name_grist)
    assert "get_value" in dir(name_grist)
    assert repr(name_grist).startswith("Grain(")
    assert "label='name'" in repr(name_grist)
    assert name_grist.get_value() == "Ada"
    assert name_grist.get_value_or_none() == "Ada"
    assert name_grist.attr_exists() is True

    del person.name

    assert name_grist.attr_exists() is False
    assert name_grist.get_value_or_none() is None
    assert name_grist.get_value(default="missing") == "missing"

    with pytest.raises(AttributeError):
        name_grist.get_value()

    name_grist.set_value("Grace")
    assert person.name == "Grace"

    with pytest.raises(CobConstraintViolationError):
        person.age = 11
