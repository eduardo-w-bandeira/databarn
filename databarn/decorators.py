from beartype import beartype
from .trails import fo
from .barn import Barn
from .cob import Cob
from .grain import Grain
from .exceptions import DataBarnSyntaxError

@beartype
def one_to_many_grain(label: str, **grain_kwargs):
    """Declare a one-to-many child relationship backed by ``Barn[ChildModel]``.

    The decorated inner Cob class becomes the child model. During outer model
    creation, DataBarn injects a Grain under ``label`` whose default factory
    builds an empty child Barn for that model.

    Args:
        label: Grain label used on the outer model.
        **grain_kwargs: Extra keyword arguments forwarded to :class:`Grain`.

    Returns:
        A class decorator that registers the decorated Cob as child model metadata.
    """
    # The decorator function that will be applied to the child Cob-like class
    @beartype
    def decorator(child_model: type[Cob]):
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
    """Declare a one-to-one child relationship backed by a child Cob type.

    The decorated inner Cob class becomes the expected type for the generated
    Grain under ``label``.

    Args:
        label: Grain label used on the outer model.
        **grain_kwargs: Extra keyword arguments forwarded to :class:`Grain`.

    Returns:
        A class decorator that registers the decorated Cob as child model metadata.
    """
    grain = Grain(**grain_kwargs)
    
    # The decorator function that will be applied to the child Cob-model
    @beartype
    def decorator(child_model: type[Cob]):
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
