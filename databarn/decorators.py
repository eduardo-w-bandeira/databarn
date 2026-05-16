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
    """Configure a Cob model's blueprint and extra-key handling.

    Args:
        blueprint: The model blueprint to apply. Must be ``static`` or
            ``dynamic``.
        on_extra_kwargs: Policy for keyword arguments that do not map to a
            declared grain. ``raise`` rejects them, ``ignore`` drops them, and
            ``create`` adds dynamic grains when the effective blueprint is
            ``dynamic``. When omitted, the policy is inferred from
            ``blueprint``.

    The decorator runs after class creation and updates the model DNA in place.

    ``on_extra_kwargs='create'`` is only valid when the effective blueprint is
    ``dynamic``.
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
    """Mark a Cob instance method as the post-initialization hook.

    The decorated method is called after the model finishes initialization.
    """
    setattr(method, POST_INIT_SYMBOL, True)
    return method

@beartype
def treat_before_assign(label: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a method as the pre-assignment hook for one grain label.

    Usage:

        @treat_before_assign('name')
        def normalize_name(self, value):
            return value.strip()

    The decorated method receives the incoming value and returns the value to
    assign.
    """
    @beartype
    def decorator(method: Callable[..., Any]) -> Callable[..., Any]:
        setattr(method, TREAT_BEFORE_ASSIGN_SYMBOL, label)
        return method

    return decorator

@beartype
def post_assign(label: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Mark a method as the post-assignment hook for one grain label.

    Usage:

        @post_assign('email')
        def validate_email(self):
            if '@' not in self.email:
                raise DataValidationError("Email must contain '@' symbol")

    The decorated method is called after the grain is assigned. Its return
    value is ignored; any exception raised by the method propagates.
    """
    @beartype
    def decorator(method: Callable[..., Any]) -> Callable[..., Any]:
        setattr(method, POST_ASSIGN_SYMBOL, label)
        return method

    return decorator

@beartype
def one_to_many_grain(label: str, **grain_kwargs) -> Callable[[type[Cob]], type[Cob]]:
    """Declare a one-to-many child relationship backed by ``Barn[ChildModel]``.

    The decorated child Cob class is stored on the generated grain metadata,
    and the outer model receives a grain whose default factory creates an empty
    child Barn for that model.

    Args:
        label: Grain label used on the outer model.
        **grain_kwargs: Extra keyword arguments forwarded to ``Grain(...)``.

    Returns:
        A class decorator that registers the decorated Cob as child-model
        metadata.
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

    The decorated child Cob class becomes the expected type for the generated
    grain under ``label``.

    Args:
        label: Grain label used on the outer model.
        **grain_kwargs: Extra keyword arguments forwarded to ``Grain(...)``.

    Returns:
        A class decorator that registers the decorated Cob as child-model
        metadata.
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
