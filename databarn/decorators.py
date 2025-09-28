from .trails import pascal_to_underscore, sentinel
from .cob import Cob
from .barn import Barn
from .grain import Grain
from .exceptions import CobConsistencyError

def wiz_create_child_barn(label: str = "", *grain_args, **grain_kwargs):
    """Decorator to define a Cob-like class as a sub-Barn seed in another Cob-like class.

    Args:
        label (str): The label of the seed. If not provided,
            it is generated from the class name in underscore_case
            and pluralized by adding 's' if it doesn't already end with 's'.
        All other args: They are passed to the Grain constructor.

    Returns:
        A decorator that sets the Cob-like class as a sub-Barn seed.
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
        grain._set_model_attrs(model=sentinel, label=label, type=Barn)
        barn = Barn(child_model)
        grain._set_pre_value(barn)
        child_model.__dna__.wiz_outer_model_grain = grain
        return child_model
    return decorator
