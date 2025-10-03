from .trails import pascal_to_underscore
from .cob import Cob
from .barn import Barn
from .grain import Grain
from .exceptions import CobConsistencyError

def wiz_create_child_barn(label: str = "", *grain_args, **grain_kwargs):
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
        Other args: All other args are passed to the Grain constructor.

    Returns:
        A decorator that sets the Cob-model as a sub-Barn grain.
    """
    grain = Grain(*grain_args, **grain_kwargs)

    # The decorator function that will be applied to the child Cob-like class
    def decorator(child_model):
        if not issubclass(child_model, Cob):
            raise CobConsistencyError("The decorated class must be a subclass of Cob.")
        nonlocal label
        if not label:
            label = pascal_to_underscore(child_model.__name__)
            label += "s" if not label.endswith("s") else ""
        grain._set_model_attrs(model=None, label=label, type=Barn)
        barn = Barn(child_model)
        grain._set_pre_value(barn)
        child_model.__dna__.wiz_outer_model_grain = grain
        return child_model
    return decorator

def wiz_create_child_cob(label: str = "", *grain_args, **grain_kwargs):
    """Decorator to define a Cob-model as a sub-Cob grain in the outer Cob-model.

    - Once this decorator is applied, the outer Cob-model will wizardly create a Grain() of
    type Cob.
    - When the outer Cob-model is instantiated, it will simply assign the default value to
    the grain (differently from the @wiz_create_child_barn decorator).
    - It's up the user to set the value to an instance of the decorated Cob-model.

    Args:
        label (str): The label of the seed. If not provided,
            it is generated from the class name in underscore_case.
        Other args: All other args are passed to the Grain constructor.

    Returns:
        A decorator that sets the Cob-like class as a sub-Cob grain.
    """
    grain = Grain(*grain_args, **grain_kwargs)
    
    # The decorator function that will be applied to the child Cob-model
    def decorator(child_model):
        if not issubclass(child_model, Cob):
            raise CobConsistencyError("The decorated class must be a subclass of Cob.")
        nonlocal label
        if not label:
            label = pascal_to_underscore(child_model.__name__)
        grain._set_model_attrs(model=None, label=label, type=Cob)
        child_model.__dna__.wiz_outer_model_grain = grain
        return child_model
    return decorator
