from typing import Type
from beartype import beartype
from .trails import fo
from .barn import Barn
from .cob import Cob
from .grain import Grain
from .exceptions import DataBarnSyntaxError

@beartype
def one_to_many_grain(label: str, **grain_kwargs):
    """Defines a sub-Barn Grain based on the given Cob-model.

    - Once this decorator is applied, the outer Cob will wizardly create a Grain() of
    type Barn.
    - When the outer Cob-model is instantiated, don't assign a value to the grain,
    because Cob will automatically create and assign a ChildModel.__dna__.create_barn() instance for it.
    - It's up the user to add instances of the decorated Cob-model class to the Barn.

    Args:
        label (str): The label of the grain.
        grain_kwargs: Kwargs to be passed to the Grain constructor.

    Returns:
        A decorator that sets the Cob-model as a sub-Barn grain.
    """
    # The decorator function that will be applied to the child Cob-like class
    @beartype
    def decorator(child_model: Type[Cob]):
        if child_model.__dna__.dynamic:
            raise DataBarnSyntaxError(fo(f"""
                Dynamic Cob-models cannot be used as child models in a Barn grain.
                You must define at least one Grain in '{child_model.__name__}',
                in order for it to be a static Cob-model."""))
        grain = Grain(factory=child_model.__dna__.create_barn, **grain_kwargs)
        grain._set_parent_model_metadata(parent_model=None, label=label, type=Barn[child_model])
        grain._set_child_model(child_model, is_child_barn=True)
        child_model.__dna__._set_outer_model_grain(grain)
        return child_model
    return decorator

@beartype
def one_to_one_grain(label: str, **grain_kwargs):
    """Defines a sub-Cob grain based on the given Cob-model.

    - Once this decorator is applied, the outer Cob-model will wizardly create a Grain() of
    type Cob.
    - When the outer Cob-model is instantiated, it will simply assign the default value to
    the grain (differently from the @one_to_many_grain).
    - It's up the user to set the value to an instance of the decorated Cob-model.

    Args:
        label (str): The label of the Grain.
        grain_kwargs: Kwargs to be passed to the Grain constructor.

    Returns:
        A decorator that sets the Cob-like class as a sub-Cob Grain.
    """
    grain = Grain(**grain_kwargs)
    
    # The decorator function that will be applied to the child Cob-model
    @beartype
    def decorator(child_model: Type[Cob]):
        if child_model.__dna__.dynamic:
            raise DataBarnSyntaxError(fo(f"""
                Dynamic Cob-models cannot be used as child models in a Cob Grain.
                You must define at least one Grain in '{child_model.__name__}',
                in order for it to be a static Cob-model."""))
        grain._set_parent_model_metadata(parent_model=None, label=label, type=child_model)
        grain._set_child_model(child_model, is_child_barn=False)
        child_model.__dna__._set_outer_model_grain(grain)
        return child_model
    return decorator
