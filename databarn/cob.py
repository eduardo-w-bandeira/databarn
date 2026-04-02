from types import SimpleNamespace 
from typing import Any
from .trails import fo
from .grain import Grain, Grist
from .dna import create_dna_class
from .exceptions import (
    CobConstraintViolationError, StaticModelViolationError,
    DataBarnSyntaxError, GrainLabelError,
    DataBarnViolationError)
from .constants import RESERVED_ATTR_NAME, ABSENT

# GLOSSARY
# label = grain var name in the cob
# key = grain key name in the dict/json output
# value = value dynamically getted from the cob attribute
# primakey = primary key value
# keyring = single primakey or tuple of composite primakeys


class MetaCob(type):
    """Metaclass that prepares Cob subclasses and attaches model DNA metadata."""

    def __new__(klass, name, bases, class_dict): # type: ignore[arg-type]
        """Build a Cob subclass and normalize declared Grain definitions.

        During class creation this method:
        - forbids reserved internal attribute names,
        - injects grains produced by relationship decorators,
        - validates that every declared Grain has a type annotation,
        - and attaches the generated ``__dna__`` class.

        Args:
            name: Name of the class being created.
            bases: Base classes for the new class.
            class_dict: Namespace dictionary used to create the class.

        Returns:
            The newly created Cob subclass.
        """
        annotations = class_dict.get('__annotations__', {})
        new_class_dict = {}
        for key, value in class_dict.items():
            if key == RESERVED_ATTR_NAME:
                raise DataBarnSyntaxError(fo(f"""
                    Cannot use protected attribute name '{key}' as a Grain label
                    in Cob-model '{name}'."""))
            new_class_dict[key] = value
            if hasattr(value, RESERVED_ATTR_NAME) and value.__dna__._outer_model_grain:
                grain: Grain = value.__dna__._outer_model_grain  # Just to clarify
                # Assign to the this model the grain created by @one_to_many_grain
                new_class_dict[grain.label] = grain
                # Update the annotation to the grain type
                annotations[grain.label] = grain.type
        for key, value in new_class_dict.items():
            if isinstance(value, Grain) and key not in annotations:
                raise DataBarnSyntaxError(fo(f"""
                    Missing type annotation for Grain '{key}' in Cob-model '{name}'.
                    Use typing.Any if unsure of the type."""))
        if annotations:  # Python naturally does not create __annotations__ if empty
            new_class_dict['__annotations__'] = annotations
        new_class = super().__new__(klass, name, bases, new_class_dict)
        new_class.__dna__ = create_dna_class(new_class)  # type: ignore[arg-type]
        return new_class


class Cob(metaclass=MetaCob):
    """Base class for DataBarn in-memory models."""

    def __init__(self, *args, **kwargs):
        """Initializes a Cob-like object.

        - Positional args are assigned to the grains in the order they were
        declared in the Cob-model (allowed only for static models).
        - Keyword args are assigned to the cob grains by name (allowed for both
        static and dynamic models).
        - If @one_to_many_grain was applied, its factory() is set
        first, before any other assignment.
        - If a grain is not assigned a value, its default is assigned.
        - If a grain is assigned both positionally and as a keyword arg, an error
        is raised.
        - If a grain is assigned that is not defined in the model, an error is
        raised for static models, or a new grain is created for dynamic models.

        After all assignments, the `__post_init__` method is called, if defined.

        Args:
            *args: positional args to be assigned to grains
            **kwargs: keyword args to be assigned to grains
        """
        dna_class = super().__getattribute__(RESERVED_ATTR_NAME)  # Bypass __getattribute__
        dna_obj = dna_class(self)  # Create an instance-level dna
        super().__setattr__(RESERVED_ATTR_NAME, dna_obj)  # Bypass __setattr__

        grists: tuple[Grist, ...] = self.__dna__.grists

        for grist in grists:
            if grist.factory:
                # grist.set_value() is just a fancy way
                # of saying setattr(self, label, value).
                # It was used for consistency along the codebase
                grist.set_value(grist.factory())

        if args and not grists:
            raise DataBarnSyntaxError(fo(f"""
                Positional args cannot be provided to initialize
                '{type(self).__name__}' because no grain has been defined
                in the Cob-model."""))

        if len(args) > len(grists):
            raise DataBarnSyntaxError(fo(f"""
                Too many positional args provided to initialize
                '{type(self).__name__}'. Expected at most {len(grists)},
                got {len(args)}."""))

        argname_value_map = {}

        # Static model assignment by position
        for index, value in enumerate(args):
            grist = grists[index]
            if grist.label in kwargs:
                raise DataBarnSyntaxError(fo(f"""
                    Cannot assign value to grain '{grist.label}' both
                    positionally and as a keyword arg."""))
            argname_value_map[grist.label] = value

        label_value_map = argname_value_map | kwargs  # Merge dicts

        if not self.__dna__.dynamic:
            for label, value in label_value_map.items():
                if label not in self.__dna__.labels:
                    raise StaticModelViolationError(fo(f"""
                        Cannot assign '{label}={value}' because the grain '{label}'
                        has not been defined in the Cob-model.
                        Since at least one grain has been defined in the Cob-model,
                        dynamic grain assignment is not allowed."""))
        else:
            for label in label_value_map.keys():
                self.__dna__._create_cereals_dynamically(label)

        for label, value in label_value_map.items():
            grist = self.__dna__.get_grist(label)
            grist.set_value(value)

        for grist in self.__dna__.grists:
            if not grist.attr_exists() and grist.default is not ABSENT:
                grist.set_value(grist.default)
            if grist.attr_exists():
                if grist.pk and grist.get_value() is None:
                    raise CobConstraintViolationError(fo(f"""
                        Primary key Grain '{grist.label}' cannot be None in Cob
                        '{type(self).__name__}'. A value must be provided
                        during initialization."""))
            elif grist.required:
                raise CobConstraintViolationError(fo(f"""
                    Missing required Grain '{grist.label}' in initialization
                    of Cob '{type(self).__name__}'. Either provide a value for
                    this grain, or set a default value in the Cob-model."""))
            # In case the value was not provided or defaulted.
            elif grist.pk and not grist.autoenum:
                raise CobConstraintViolationError(fo(f"""
                    Missing primary key Grain '{grist.label}' in initialization
                    of Cob '{type(self).__name__}'. Primary key Grains must be
                    provided with a value during initialization."""))
            elif grist.unique and not grist.autoenum:
                raise CobConstraintViolationError(fo(f"""
                    Missing unique Grain '{grist.label}' in initialization
                    of Cob '{type(self).__name__}'. Unique Grains must be
                    provided with a value during initialization."""))


        if hasattr(self, "__post_init__"):
            self.__post_init__()

    def __getattribute__(self, name: str) -> Any:
        """Return an attribute while preventing fallback to class-level Grain defaults.

        If a Grain label exists in the model but its value is currently unset in
        this instance, this method raises ``AttributeError`` instead of falling
        back to the class attribute.

        Args:
            name: Attribute name to retrieve.

        Returns:
            The resolved attribute value.
        """
        self_dict = super().__getattribute__('__dict__')
        dna = super().__getattribute__(RESERVED_ATTR_NAME)
        # If the labels exists in __dna__.labels, but not in __dict__,
        # it means it has been deleted or not set.
        # This method prevents falling back to class attributes.
        if name not in self_dict and name in dna.labels:
            raise AttributeError(fo(f"""
                Attribute '{name}' has not been set for this Cob instance, or it was deleted.
                Although the Grain '{name}' exists in the Cob-model, it currently has no value."""))
        return super().__getattribute__(name)

    def __setattr__(self, label: str, value: Any):
        """Set a Grain value with validation and relationship bookkeeping.

        Args:
            label: Target Grain label.
            value: Value to assign.
        """
        if label == RESERVED_ATTR_NAME:
            raise DataBarnViolationError(fo(f"""
                Cannot assign to protected attribute '{label}'.
                This attribute is reserved for internal DataBarn state."""))
        grist: Grist | None = self.__dna__.get_grist(label, default=None)
        if not grist:
            # If the Cob-model is static, _create_cereals_dynamically() will raise an error
            output: SimpleNamespace = self.__dna__._create_cereals_dynamically(label)
            grist = output.grist
        self.__dna__._verify_constraints(grist, value)
        self.__dna__._remove_prev_value_parent_if(grist, new_value=value)
        super().__setattr__(label, value)
        self.__dna__._set_parent_for_new_value_if(grist)

    def __delattr__(self, label: str) -> None:
        """Delete a Grain value while enforcing deletion constraints.

        Args:
            label: Grain label to delete.
        """
        if label == RESERVED_ATTR_NAME:
            raise DataBarnViolationError(fo(f"""
                Cannot delete protected attribute '{label}'.
                This attribute is reserved for internal DataBarn state."""))
        grist: Grist | None = self.__dna__.get_grist(label, default=None)
        if grist:
            if grist.pk:
                raise CobConstraintViolationError(fo(f"""
                    Cannot delete attribute '{label}' because the Grain
                    was defined with 'pk=True' (primary key)."""))
            if grist.frozen:
                raise CobConstraintViolationError(fo(f"""
                    Cannot delete attribute '{label}' because the Grain
                    was defined with 'frozen=True'."""))
            if grist.required:
                raise CobConstraintViolationError(fo(f"""
                    Cannot delete attribute '{label}' because the Grain
                    was defined with 'required=True'."""))
            self.__dna__._remove_prev_value_parent_if(
                grist, new_value=None)  # Fictitious new value
            if self.__dna__.dynamic:
                self.__dna__._remove_cereals_dynamically(label)
        super().__delattr__(label)

    def __getitem__(self, label: str) -> Any:
        """Return a Grain value using mapping-style access.

        Only Grain labels are supported by this access pattern.

        Args:
            label: Grain label.

        Returns:
            The current value of the Grain.
        """
        grist: Grist | None = self.__dna__.get_grist(label, default=None)
        if not grist:
            if hasattr(self, label):
                raise DataBarnSyntaxError(fo(f"""
                    Attribute '{label}' exists in Cob '{type(self).__name__}', but it is not a Grain.
                    Only Grain attributes can be accessed using this syntax."""))
            raise KeyError(fo(f"""
                Grain '{label}' not found in Cob '{type(self).__name__}'."""))
        return getattr(self, label)

    def __setitem__(self, label: str, value: Any) -> None:
        """Assign a Grain value using mapping-style syntax.

        Args:
            label: Grain label.
            value: Value to assign.
        """
        if label == RESERVED_ATTR_NAME:
            raise DataBarnViolationError(fo(f"""
                Cannot assign to protected key '{label}'.
                This key is reserved for internal DataBarn state."""))
        if type(label) is not str or not label.isidentifier():
            raise GrainLabelError(fo(f"""
                Cannot convert key '{label}' to a valid var name.
                Grain labels must be valid Python identifiers."""))
        setattr(self, label, value)

    def __delitem__(self, label: str) -> None:
        """Delete a Grain value using mapping-style syntax.

        Args:
            label: Grain label.
        """
        if label == RESERVED_ATTR_NAME:
            raise GrainLabelError(fo(f"""
                Cannot delete protected key '{label}'.
                This key is reserved for internal DataBarn state."""))
        if label not in self.__dna__.labels:
            if hasattr(self, label):
                raise DataBarnSyntaxError(fo(f"""
                    Attribute '{label}' exists in Cob '{type(self).__name__}', but it is not a Grain.
                    Only Grain attributes can be deleted using this syntax."""))
            raise KeyError(fo(f"""
                Grain '{label}' not found in Cob '{type(self).__name__}'."""))
        delattr(self, label)

    def __contains__(self, label: str) -> bool:
        """Return whether a Grain currently has an active value on this instance.

        *ATTENTION*: If the attribute was deleted, it will return False,
        even if the Grain still exists in the Cob-model.

        Args:
            label: Grain label.

        Returns:
            True if the label exists in active grists, otherwise False.
        """
        return label in [grist.label for grist in self.__dna__.active_grists]

    def __eq__(self, other_cob) -> bool:
        """Check equality between two Cob objects based on comparable Grains.

        As a rule, comparisons require at least the definition of one comparable grain.
        However, there's an exception: if both objects are the same, they are considered equal.
        In all other cases, the comparison is based on comparable grists.

        All comparable grists must be equal for the objects to be considered equal."""
        if self is other_cob:
            # As a rule, comparisons require at least the definition of a comparable grain,
            # But if they are the same object, they are equal anyway.
            return True
        if not isinstance(other_cob, Cob):
            return False
        comparables = self.__dna__._check_and_get_comparables(other_cob)
        for self_grist in comparables:
            other_grist = other_cob.__dna__.get_grist(self_grist.label)
            if self_grist.get_value() != other_grist.get_value():
                return False
        return True

    def __ne__(self, other_cob) -> bool:
        """Return logical negation of :meth:`__eq__`."""
        return not self.__eq__(other_cob)

    def __gt__(self, other_cob) -> bool:
        """Return whether all comparable grists are greater than ``other_cob``.

        All comparable grists in ``self`` must be greater than corresponding
        grists in ``other_cob``.
        """
        comparables = self.__dna__._check_and_get_comparables(other_cob)
        for grist in comparables:
            self_val = getattr(self, grist.label)
            other_val = getattr(other_cob, grist.label)
            if self_val <= other_val:
                return False
        return True

    def __ge__(self, other_cob) -> bool:
        """Return whether all comparable grists are >= ``other_cob``.

        All comparable grists in ``self`` must be greater than or equal to
        corresponding grists in ``other_cob``.
        """
        comparables = self.__dna__._check_and_get_comparables(other_cob)
        for grist in comparables:
            self_val = getattr(self, grist.label)
            other_val = getattr(other_cob, grist.label)
            if self_val < other_val:
                return False
        return True

    def __lt__(self, other_cob) -> bool:
        """Return whether all comparable grists are less than ``other_cob``.

        All comparable grists in ``self`` must be less than corresponding
        grists in ``other_cob``.
        """
        comparables = self.__dna__._check_and_get_comparables(other_cob)
        for grist in comparables:
            self_val = getattr(self, grist.label)
            other_val = getattr(other_cob, grist.label)
            if self_val >= other_val:
                return False
        return True

    def __le__(self, other_cob) -> bool:
        """Return whether all comparable grists are <= ``other_cob``.

        All comparable grists in ``self`` must be less than or equal to
        corresponding grists in ``other_cob``.
        """
        comparables = self.__dna__._check_and_get_comparables(other_cob)
        for grist in comparables:
            self_val = getattr(self, grist.label)
            other_val = getattr(other_cob, grist.label)
            if self_val > other_val:
                return False
        return True

    def __repr__(self) -> str:
        """Return a repr showing all model grists and their current values."""
        items = []
        for grist in self.__dna__.active_grists:
            items.append(f"{grist.label}={grist.get_value()!r}")
        in_commas = ", ".join(items)
        return f"{type(self).__name__}({in_commas})"
