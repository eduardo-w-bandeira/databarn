from types import SimpleNamespace as Namespace
from typing import Any
from .trails import fo
from .grain import Grain, Grist
from .dna import dna_factory
from .exceptions import CobConstraintViolationError, StaticModelViolationError, DataBarnSyntaxError, InvalidGrainLabelError
from .constants import RESERVED_ATTR_NAME, ABSENT

# GLOSSARY
# label = grain var name in the cob
# key = grain key name in the dict/json output
# value = value dynamically getted from the cob attribute
# primakey = primary key value
# keyring = single primakey or tuple of composite primakeys


class MetaCob(type):
    """Sets the __dna__ attribute for the Cob-model."""

    def __new__(klass, name, bases, class_dict):
        annotations = class_dict.get('__annotations__', {})
        new_dict = {}
        for key, value in class_dict.items():
            if key == RESERVED_ATTR_NAME:
                raise InvalidGrainLabelError(fo(f"""
                    Cannot use protected attribute name '{key}' as a Grain label
                    in Cob-model '{name}'."""))
            new_dict[key] = value
            if hasattr(value, RESERVED_ATTR_NAME) and value.__dna__._outer_model_grain:
                grain: Grain = value.__dna__._outer_model_grain  # Just to clarify
                # Assign to the this model the grain created by @one_to_many_grain
                new_dict[grain.label] = grain
                # Update the annotation to the grain type
                annotations[grain.label] = grain.type
        for key, value in new_dict.items():
            if isinstance(value, Grain) and key not in annotations:
                raise DataBarnSyntaxError(fo(f"""
                    Missing type annotation for Grain '{key}' in Cob-model '{name}'.
                    Use typing.Any if unsure of the type."""))
        if annotations:  # Python naturally does not create __annotations__ if empty
            new_dict['__annotations__'] = annotations
        new_class = super().__new__(klass, name, bases, new_dict)
        new_class.__dna__ = dna_factory(new_class)
        return new_class


class Cob(metaclass=MetaCob):
    """The base class for all in-memory data models."""

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
        dna_obj = dna_class(self)  # Create an object-level dna
        super().__setattr__(RESERVED_ATTR_NAME, dna_obj)  # Bypass __setattr__

        grists = self.__dna__.grists

        for grist in grists:
            if grist.factory:
                # Just a fancy way of saying setattr(self, label, value)
                # Used for consistency along the codebase
                grist.set_value(grist.factory())

        if self.__dna__.dynamic and args:
            raise DataBarnSyntaxError(fo(f"""
                Positional args cannot be provided to initialize
                '{type(self).__name__}' because no grain has been defined
                in the Cob-model. Use only keyword args to assign
                grain values dynamically."""))
        elif len(args) > len(grists):
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
            # In case the value was not provided or defaulted.
            elif grist.pk and not grist.autoenum:
                raise CobConstraintViolationError(fo(f"""
                    Missing primary key Grain '{grist.label}' in initialization
                    of Cob '{type(self).__name__}'. Primary key Grains must be
                    provided with a value during initialization."""))
            elif grist.required:
                raise CobConstraintViolationError(fo(f"""
                    Missing required Grain '{grist.label}' in initialization
                    of Cob '{type(self).__name__}'. Either provide a value for
                    this grain, or set a default value in the Cob-model."""))
            

        if hasattr(self, "__post_init__"):
            self.__post_init__()

    def __getattribute__(self, name: str) -> Any:
        self_dict = super().__getattribute__('__dict__')
        dna = super().__getattribute__(RESERVED_ATTR_NAME)
        # If the labels exists in __dna__.labels, but not in __dict__,
        # it means it has been deleted.
        # This method prevents falling back to class attributes.
        if name in dna.labels and name not in self_dict:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'")
        return super().__getattribute__(name)

    def __setattr__(self, label: str, value: Any):
        """Sets the attribute value, with type and constraint checks for the Grain.

        Args:
            label (str): The Grain name.
            value (Any): The Grain value.
        """
        grist: Grist | None = self.__dna__.get_grist(label, default=None)
        if not grist:
            # If the Cob-model is static, _create_cereals_dynamically() will raise an error
            output: Namespace = self.__dna__._create_cereals_dynamically(label)
            grist = output.grist
        self.__dna__._verify_constraints(grist, value)
        self.__dna__._remove_prev_value_parent_if(grist, new_value=value)
        super().__setattr__(label, value)
        self.__dna__._set_parent_for_new_value_if(grist)

    def __delattr__(self, label: str) -> None:
        """Deletes the attribute value. This is allowed for both static and dynamic models.

        Args:
            label (str): The Grain label.
        """
        grist = self.__dna__.get_grist(label, default=None)
        if grist:
            if grist.frozen:
                raise CobConstraintViolationError(fo(f"""
                    Cannot delete attribute '{label}' because the Grain was defined with
                    'frozen=True'."""))
            if grist.pk and self.__dna__.barns:
                raise CobConstraintViolationError(fo(f"""
                    Cannot delete primary key attribute '{label}' because the Cob is stored in a Barn.
                    Primary key Grains cannot be deleted from Cobs that are stored in Barns."""))
            self.__dna__._remove_prev_value_parent_if(
                grist, new_value=None)  # Fictitious new value
            if self.__dna__.dynamic:
                self.__dna__._remove_cereals_dynamically(label)
        super().__delattr__(label)

    def __getitem__(self, label: str) -> Any:
        """Access grist values in a dictionary-like way.
        Other attributes are not accessible this way.

        Args:
            label (str): The Grain label.
        Returns:
            Any: The grist value.
        """
        grist = self.__dna__.get_grist(label, default=None)
        if not grist:
            raise KeyError(fo(f"""
                Cob-model '{type(self).__name__}' has no Grain '{label}'."""))
        try:
            return getattr(self, label)
        except AttributeError:
            raise KeyError(fo(f"""
                Cob '{type(self).__name__}' has no key '{label}',
                although the Grain exists in the Cob-model.""")) from None

    def __setitem__(self, label: str, value: Any) -> None:
        """Set grist values in a dictionary-like way.
        Other attributes are not settable this way.

        Args:
            label (str): The Grain name.
            value (Any): The Grain value.
        """
        if type(label) is not str or not label.isidentifier():
            raise InvalidGrainLabelError(fo(f"""
                Cannot convert key '{label}' to a valid var name.
                Grain labels must be valid Python identifiers."""))
        setattr(self, label, value)

    def __delitem__(self, label: str) -> None:
        """Delete grain values in a dictionary-like way.

        Args:
            label (str): The Grain name.
        """
        if label not in self.__dna__.labels:
            raise KeyError(
                f"Grain '{label}' not found in Cob '{type(self).__name__}'.")
        delattr(self, label)

    def __contains__(self, label: str) -> bool:
        """Allow use of 'in' keyword to check if a Grain label exists in the Cob.

        *ATTENTION*: If the attribute was deleted, it will return False,
        even if the Grain still exists in the Cob-model.

        Args:
            label (str): The Grain label.

        Returns:
            bool: True if the label exists in the Cob, False otherwise.
        """
        return label in [grist.label for grist in self.__dna__.grists]

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
        """Check inequality between two Cob objects based on comparable grists."""
        return not self.__eq__(other_cob)

    def __gt__(self, other_cob) -> bool:
        """Check if self is greater than value based on comparable grists.

        All comparable grists in self must be greater than those in value
        to return True, otherwise returns False.
        """
        comparables = self.__dna__._check_and_get_comparables(other_cob)
        for grist in comparables:
            self_val = getattr(self, grist.label)
            other_val = getattr(other_cob, grist.label)
            if self_val <= other_val:
                return False
        return True

    def __ge__(self, other_cob) -> bool:
        """Check if self is greater than or equal to value based on comparable grists.

        All comparable grists in self must be greater than or equal to those in value
        to return True, otherwise returns False."""
        comparables = self.__dna__._check_and_get_comparables(other_cob)
        for grist in comparables:
            self_val = getattr(self, grist.label)
            other_val = getattr(other_cob, grist.label)
            if self_val < other_val:
                return False
        return True

    def __lt__(self, other_cob) -> bool:
        """Check if self is less than value based on comparable grists.

        All comparable grists in self must be less than those in value
        to return True, otherwise returns False."""
        comparables = self.__dna__._check_and_get_comparables(other_cob)
        for grist in comparables:
            self_val = getattr(self, grist.label)
            other_val = getattr(other_cob, grist.label)
            if self_val >= other_val:
                return False
        return True

    def __le__(self, other_cob) -> bool:
        """Check if self is less than or equal to value based on comparable grists.

        All comparable grists in self must be less than or equal to those in value
        to return True, otherwise returns False."""
        comparables = self.__dna__._check_and_get_comparables(other_cob)
        for grist in comparables:
            self_val = getattr(self, grist.label)
            other_val = getattr(other_cob, grist.label)
            if self_val > other_val:
                return False
        return True

    def __repr__(self) -> str:
        items = []
        for grist in self.__dna__.grists:
            items.append(f"{grist.label}={grist.get_value()!r}")
        in_commas = ", ".join(items)
        return f"{type(self).__name__}({in_commas})"
