import pytest

from databarn import Barn, Cob, one_to_many_grain, one_to_one_grain
from databarn.exceptions import DataBarnSyntaxError


def test_one_to_many_grain_registers_child_metadata_and_factory() -> None:
    class Parent(Cob):
        title: str

        @one_to_many_grain("children", key="children_data")
        class Child(Cob):
            name: str

    grain = Parent.__dna__.get_grain("children")
    parent = Parent(title="family")
    created_barn = grain.factory()

    assert grain.parent_model is Parent
    assert grain.child_model is Parent.Child
    assert grain.is_child_barn is True
    assert isinstance(created_barn, Barn)
    assert created_barn.model is Parent.Child
    assert list(created_barn) == []
    assert Parent.Child.__dna__._outer_model_grain is grain
    assert isinstance(parent.children, Barn)
    assert list(parent.children) == []
    assert parent.__dna__.to_dict() == {"title": "family", "children_data": []}


def test_one_to_one_grain_registers_child_metadata_and_forwards_kwargs() -> None:
    class Parent(Cob):

        @one_to_one_grain("profile", required=True, key="profile_data")
        class Profile(Cob):
            name: str

    grain = Parent.__dna__.get_grain("profile")
    parent = Parent(profile=Parent.Profile(name="Ada"))

    assert grain.parent_model is Parent
    assert grain.child_model is Parent.Profile
    assert grain.is_child_barn is False
    assert grain.factory is None
    assert grain.required is True
    assert grain.key == "profile_data"
    assert Parent.Profile.__dna__._outer_model_grain is grain
    assert parent.profile.name == "Ada"
    assert parent.__dna__.to_dict() == {"profile_data": {"name": "Ada"}}


def test_one_to_many_grain_rejects_dynamic_child_models() -> None:
    with pytest.raises(DataBarnSyntaxError):

        @one_to_many_grain("children")
        class Child(Cob):
            pass


def test_one_to_one_grain_rejects_dynamic_child_models() -> None:
    with pytest.raises(DataBarnSyntaxError):

        @one_to_one_grain("child")
        class Child(Cob):
            pass
