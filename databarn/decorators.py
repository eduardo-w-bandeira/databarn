from typing import Type
from .trails import pascal_to_underscore, fo
from .barn import Barn
from .cob import Cob
from .grain import Grain
from .exceptions import DataBarnSyntaxError


def create_child_barn_grain(label: str = "", frozen: bool = True, **grain_kwargs):
    """Decorator to define a Cob-like class as a sub-Barn grain in the outer Cob-model.

    - Once this decorator is applied, the outer Cob will wizardly create a Grain() of
    type Barn.
    - When the outer Cob-model is instantiated, don't assign a value to the grain,
    because Cob will automatically create and assign a Barn(ChildModel) instance for it.
    - It's up the user to add instances of the decorated Cob-model class to the Barn.

    Args:
        label (str): The label of the grain. If not provided,
            it is generated from the class name in underscore_case
            and pluralized by adding 's' if it doesn't already end with 's'.
        frozen (bool): Whether the grain is frozen (immutable) after being set once.
            Default is True.
        grain_kwargs: Kwargs to be passed to the Grain constructor.

    Returns:
        A decorator that sets the Cob-model as a sub-Barn grain.
    """
    # The decorator function that will be applied to the child Cob-like class
    def decorator(child_model: Type[Cob]):
        if not issubclass(child_model, Cob):
            raise DataBarnSyntaxError("The decorated class must be a subclass of Cob.")
        if child_model.__dna__.dynamic:
            raise DataBarnSyntaxError(fo(f"""
                Dynamic Cob-models cannot be used as child models in a Barn grain.
                You must define at least one Grain in '{child_model.__name__}',
                in order for it to be a static Cob-model."""))
        nonlocal label
        if not label:
            label = pascal_to_underscore(child_model.__name__)
            label += "s" if not label.endswith("s") else ""
        grain = Grain(
            frozen=frozen, factory=child_model.__dna__.create_barn, **grain_kwargs)
        grain._set_model_attrs(model=None, label=label, type=Barn)
        grain._set_child_model(child_model, is_child_barn_ref=True)
        child_model.__dna__._set_outer_model_grain(grain)
        return child_model
    return decorator

def create_child_cob_grain(label: str = "", **grain_kwargs):
    """Decorator to define a Cob-model as a sub-Cob grain in the outer Cob-model.

    - Once this decorator is applied, the outer Cob-model will wizardly create a Grain() of
    type Cob.
    - When the outer Cob-model is instantiated, it will simply assign the default value to
    the grain (differently from the @create_child_barn_grain).
    - It's up the user to set the value to an instance of the decorated Cob-model.

    Args:
        label (str): The label of the seed. If not provided,
            it is generated from the class name in underscore_case.
        grain_kwargs: Kwargs to be passed to the Grain constructor.

    Returns:
        A decorator that sets the Cob-like class as a sub-Cob grain.
    """
    grain = Grain(**grain_kwargs)
    
    # The decorator function that will be applied to the child Cob-model
    def decorator(child_model: Type[Cob]):
        if not issubclass(child_model, Cob):
            raise DataBarnSyntaxError("The decorated class must be a subclass of Cob.")
        if child_model.__dna__.dynamic:
            raise DataBarnSyntaxError(fo(f"""
                Dynamic Cob-models cannot be used as child models in a Cob Grain.
                You must define at least one Grain in '{child_model.__name__}',
                in order for it to be a static Cob-model."""))
        nonlocal label
        if not label:
            label = pascal_to_underscore(child_model.__name__)
        grain._set_model_attrs(model=None, label=label, type=child_model)
        grain._set_child_model(child_model, is_child_barn_ref=False)
        child_model.__dna__._set_outer_model_grain(grain)
        return child_model
    return decorator
