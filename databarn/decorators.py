from collections.abc import Callable
from typing import Any

from beartype import beartype
from .constants import POST_INIT_ATTR_NAME, BEFORE_ASSIGN_ATTR_NAME, POST_ASSIGN_ATTR_NAME
from .trails import fo
from .barn import Barn
from .cob import Cob
from .grain import create_grain_class
from .exceptions import DataBarnSyntaxError


@beartype
def post_init(method: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a Cob instance method as the post-initialization hook."""
    setattr(method, POST_INIT_ATTR_NAME, True)
    return method

@beartype
def treat_before_assign(label: str):
    """Decorator factory that marks a Cob instance method as a preprocessor
    for a specific grain label.

    Usage:

        @treat_before_assign('name')
        def normalize_name(self, value):
            return value.strip()

    The decorated method should accept a single argument (the value) and
    return the transformed value. The decorator stores the target label on
    the function object so assignment logic can invoke it only when the
    matching grain is being set.
    """
    @beartype
    def decorator(method: Callable[..., Any]) -> Callable[..., Any]:
        setattr(method, BEFORE_ASSIGN_ATTR_NAME, label)
        return method

    return decorator

@beartype
def post_assign(label: str):
    """Decorator factory that marks a Cob instance method as a post-processor
    for a specific grain label.

    Usage:

        @post_assign('email')
        def validate_email(self):
            if '@' not in self.email:
                raise ValidationError("Email must contain '@' symbol")

    The decorated method should accept no arguments (only self) and will be
    invoked after the grain is assigned. If the method raises an error, the
    error propagates and the assignment is considered failed. The return value
    is ignored. It is recommended to raise ValidationError for validation
    failures to maintain consistency with DataBarn's error handling conventions.
    """
    @beartype
    def decorator(method: Callable[..., Any]) -> Callable[..., Any]:
        setattr(method, POST_ASSIGN_ATTR_NAME, label)
        return method

    return decorator

@beartype
def one_to_many_grain(label: str, **grain_kwargs):
    """Declare a one-to-many child relationship backed by ``Barn[ChildModel]``.

    The decorated inner Cob class becomes the child model. During outer model
    creation, DataBarn injects a Grain under ``label`` whose default factory
    builds an empty child Barn for that model.

    Args:
        label: Grain label used on the outer model.
        **grain_kwargs: Extra keyword arguments forwarded to ``Grain(...)``.

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
        grain = create_grain_class(factory=child_model.__dna__.create_barn, **grain_kwargs)
        grain.__setup__(parent_model=None, label=label, type=Barn[child_model])
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
        **grain_kwargs: Extra keyword arguments forwarded to ``Grain(...)``.

    Returns:
        A class decorator that registers the decorated Cob as child model metadata.
    """
    grain = create_grain_class(**grain_kwargs)
    
    # The decorator function that will be applied to the child Cob-model
    @beartype
    def decorator(child_model: type[Cob]):
        if child_model.__dna__.dynamic:
            raise DataBarnSyntaxError(fo(f"""
                Dynamic Cob-models cannot be used as child models in a Cob Grain.
                You must define at least one Grain in '{child_model.__name__}',
                in order for it to be a static Cob-model."""))
        grain.__setup__(parent_model=None, label=label, type=child_model)
        grain._set_child_model(child_model, is_child_barn=False)
        child_model.__dna__._set_outer_model_grain(grain)
        return child_model
    return decorator
