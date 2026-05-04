from collections.abc import Callable
from typing import Any

from beartype import beartype
from .constants import POST_INIT_SYMBOL, TREAT_BEFORE_ASSIGN_SYMBOL, POST_ASSIGN_SYMBOL
from .trails import fo
from .barn import Barn
from .cob import Cob
from .grain import create_grain_class
from .exceptions import DataBarnSyntaxError
from .constants import (
    DNA_SYMBOL, STATIC, DYNAMIC, BLUEPRINTS, ON_EXTRA_KWARGS_OPTIONS,
    ON_EXTRA_KWARGS_CREATE, ON_EXTRA_KWARGS_RAISE,)

@beartype
def config_cob(blueprint: str = STATIC, on_extra_kwargs: str | None = None) -> Callable[[type[Cob]], type[Cob]]:
    """Class decorator to configure the Cob-model blueprint.

    Args:
        blueprint: One of 'static' or 'dynamic'. Defaults to 'static'.
        on_extra_kwargs: How to handle keyword arguments that do not match a
            declared grain: ``'raise'`` raises ``ValidationError``,
            ``'ignore'`` drops them, and ``'create'`` adds dynamic grains
            (requires an effective ``dynamic`` blueprint; see below).
            Defaults to ``None`` and is resolved by blueprint:
            ``static -> raise`` and ``dynamic -> create``.

    The decorator runs after class creation (and after the metaclass has
    attached the model `__dna__`) and updates the model DNA's `blueprint`
    and ``on_extra_kwargs`` attributes.

    For ``on_extra_kwargs='create'``, either the ``blueprint`` argument must
    be ``dynamic`` or the model's DNA blueprint before decoration must be
    ``dynamic``; otherwise :class:`DataBarnSyntaxError` is raised. After
    applying ``blueprint``, the effective blueprint must still be ``dynamic``.
    """
    if blueprint not in BLUEPRINTS:
        raise DataBarnSyntaxError(fo(f"""
            Invalid blueprint '{blueprint}'.
            Allowed values are: {', '.join(BLUEPRINTS)}."""))
    if on_extra_kwargs is None:
        on_extra_kwargs = (
            ON_EXTRA_KWARGS_CREATE if blueprint == DYNAMIC
            else ON_EXTRA_KWARGS_RAISE)
    if on_extra_kwargs not in ON_EXTRA_KWARGS_OPTIONS:
        raise DataBarnSyntaxError(fo(f"""
            Invalid on_extra_kwargs '{on_extra_kwargs}'. Allowed values are:
            {', '.join(ON_EXTRA_KWARGS_OPTIONS)}."""))
    if on_extra_kwargs == ON_EXTRA_KWARGS_CREATE:
        if blueprint != DYNAMIC:
            raise DataBarnSyntaxError(fo(f"""
                Cannot use on_extra_kwargs='create' on '{blueprint}' blueprint:
                blueprint must be '{DYNAMIC}'."""))

    @beartype
    def decorator(model: type[ Cob ]):
        dna = getattr(model, DNA_SYMBOL, None)
        if dna is None:
            raise DataBarnSyntaxError(fo(f"""
                Cannot apply @config_cob to '{model.__name__}': model DNA not initialized.
            """))
        dna.blueprint = blueprint
        dna.on_extra_kwargs = on_extra_kwargs
        return model

    return decorator


@beartype
def post_init(method: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a Cob instance method as the post-initialization hook."""
    setattr(method, POST_INIT_SYMBOL, True)
    return method

@beartype
def treat_before_assign(label: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
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
        setattr(method, TREAT_BEFORE_ASSIGN_SYMBOL, label)
        return method

    return decorator

@beartype
def post_assign(label: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
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
        setattr(method, POST_ASSIGN_SYMBOL, label)
        return method

    return decorator

@beartype
def one_to_many_grain(label: str, **grain_kwargs) -> Callable[[type[Cob]], type[Cob]]:
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
        if child_model.__dna__.blueprint == "dynamic":
            raise DataBarnSyntaxError(fo(f"""
                Dynamic Cob-models cannot be used as child models in a Barn grain.
                You must define at least one Grain in '{child_model.__name__}',
                in order for it to be a static Cob-model."""))
        grain = create_grain_class(factory=child_model.__dna__.create_barn, **grain_kwargs)
        grain._set_relationship_data(label=label, type=Barn[child_model],
            child_model=child_model, is_child_barn=True)
        child_model.__dna__._set_outer_model_grain(grain)
        return child_model
    return decorator

@beartype
def one_to_one_grain(label: str, **grain_kwargs) -> Callable[[type[Cob]], type[Cob]]:
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
        if child_model.__dna__.blueprint == "dynamic":
            raise DataBarnSyntaxError(fo(f"""
                Dynamic Cob-models cannot be used as child models in a Cob Grain.
                You must define at least one Grain in '{child_model.__name__}',
                in order for it to be a static Cob-model."""))
        grain._set_relationship_data(label=label, type=child_model,
            child_model=child_model, is_child_barn=False)
        child_model.__dna__._set_outer_model_grain(grain)
        return child_model
    return decorator
