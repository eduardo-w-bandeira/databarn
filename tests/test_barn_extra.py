import pytest

from databarn import Barn, Cob, Grain
from databarn.exceptions import DataBarnSyntaxError


def test_get_with_labeled_keys_on_dynamic_model_raises() -> None:
    class DynamicCob(Cob):
        pass

    barn = Barn(DynamicCob)

    with pytest.raises(DataBarnSyntaxError):
        # dynamic model cannot be queried with labeled primakey kwargs
        barn.get(id=1)


def test_remove_non_stored_cob_raises_keyerror() -> None:
    class Person(Cob):
        id: int = Grain(pk=True)

    barn = Barn(Person)
    person = Person(id=1)

    with pytest.raises(KeyError):
        # removing a cob that was never added should raise KeyError
        barn.remove(person)
