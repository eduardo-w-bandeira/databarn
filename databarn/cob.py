from typing import Any
from .trails import fo
from .grain import Grain
from .dna import dna_factory
from .exceptions import StaticModelViolationError, DataBarnSyntaxError, InvalidGrainLabelError
from .constants import RESERVED_ATTR_NAME

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
                # Assign to the this model the grain created by @create_child_barn_grain
                new_dict[grain.label] = grain
                # Update the annotation to the grain type
                annotations[grain.label] = grain.type
        for key, value in new_dict.items():
            if isinstance(value, Grain) and key not in annotations:
                raise DataBarnSyntaxError(fo(f"""
                    Missing type annotation for Grain '{key}' in Cob-model '{name}'.
                    Use typing.Any if unsure of the type."""))
        if annotations: # Python naturally does not create __annotations__ if empty
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
        - If @create_child_barn_grain was applied, its factory() is set
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
        dna = self.__dna__(self)  # Create an object-level __dna__
        self.__dict__.update(__dna__=dna)  # Bypass __setattr__

        seeds = self.__dna__.seeds

        for seed in seeds:
            if seed.factory:
                setattr(self, seed.label, seed.factory())

        if self.__dna__.dynamic and args:
            raise DataBarnSyntaxError(fo(f"""
                Positional args cannot be provided to initialize
                '{type(self).__name__}' because no grain has been defined
                in the Cob-model. Use only keyword args to assign
                grain values dynamically."""))
        elif len(args) > len(seeds):
            raise DataBarnSyntaxError(fo(f"""
                Too many positional args provided to initialize
                '{type(self).__name__}'. Expected at most {len(seeds)},
                got {len(args)}."""))

        argname_value_map = {}

        # Static model assignment by position
        for index, value in enumerate(args):
            seed = seeds[index]
            if seed.label in kwargs:
                raise DataBarnSyntaxError(fo(f"""
                    Cannot assign value to grain '{seed.label}' both
                    positionally and as a keyword arg."""))            
            argname_value_map[seed.label] = value

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
                self.__dna__.add_grain_dynamically(label)

        for label, value in label_value_map.items():
            setattr(self, label, value)

        for seed in seeds:
            if not seed.has_been_set:
                setattr(self, seed.label, seed.default)

        if hasattr(self, "__post_init__"):
            self.__post_init__()

    def __setattr__(self, label: str, value: Any):
        """Sets the attribute value, with type and constraint checks for the seed.

        Args:
            label (str): The grain name.
            value (Any): The grain value.
        """
        seed = self.__dna__.get_seed(label, default=None)
        if not seed:
            # If the model is static, add_grain_dynamically() will raise an error
            self.__dna__.add_grain_dynamically(label)
            seed = self.__dna__.get_seed(label)
        self.__dna__._verify_constraints(seed, value)
        self.__dna__._remove_prev_value_parent_if(seed, new_value=value)
        super().__setattr__(label, value)
        self.__dna__._set_parent_for_new_value_if(seed)

    def __delattr__(self, label: str) -> None:
        """Deletes the attribute value, with checks for dynamic models.

        Args:
            label (str): The grain label.
        """
        if label in self.__dna__.labels:
            seed = self.__dna__.get_seed(label)
            self.__dna__._remove_grain_dynamically(
                label)  # Raises error if static
            self.__dna__._remove_prev_value_parent_if(
                seed, new_value=None)  # Fictitious new value
        super().__delattr__(label)

    def __getitem__(self, label: str) -> Any:
        """Access seed values in a dictionary-like way.
        Other attributes are not accessible this way.

        Args:
            label (str): The Grain label.
        Returns:
            Any: The seed value.
        """
        seed = self.__dna__.get_seed(label, None)
        if not seed:
            raise KeyError(
                f"Grain '{label}' not found in Cob '{type(self).__name__}'.")
        return getattr(self, label)

    def __setitem__(self, label: str, value: Any) -> None:
        """Set seed values in a dictionary-like way.
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
        """Allow use of 'in' keyword to check if a grain label exists in the Cob.

        Args:
            label (str): The grain name.

        Returns:
            bool: True if the Grain exists, False otherwise.
        """
        return label in self.__dna__.labels

    def __eq__(self, other_cob: Any) -> bool:
        """Check equality between two Cob objects based on comparable grains.

        As a rule, comparisons require at least the definition of one comparable grain.
        However, there's an exception: if both objects are the same, they are considered equal.
        In all other cases, the comparison is based on comparable seeds.

        All comparable seeds must be equal for the objects to be considered equal."""
        if self is other_cob:
            # As a rule, comparisons require at least the definition of a comparable grain,
            # But if they are the same object, they are equal anyway.
            return True
        if not isinstance(other_cob, Cob):
            return False
        comparables = self.__dna__._check_and_get_comparables(other_cob)
        for self_seed in comparables:
            other_seed = other_cob.__dna__.get_seed(self_seed.label)
            if self_seed.get_value() != other_seed.get_value():
                return False
        return True

    def __ne__(self, other_cob) -> bool:
        """Check inequality between two Cob objects based on comparable seeds."""
        return not self.__eq__(other_cob)

    def __gt__(self, other_cob) -> bool:
        """Check if self is greater than value based on comparable seeds.

        All comparable seeds in self must be greater than those in value
        to return True, otherwise returns False.
        """
        comparables = self.__dna__._check_and_get_comparables(other_cob)
        for seed in comparables:
            self_val = getattr(self, seed.label)
            other_val = getattr(other_cob, seed.label)
            if self_val <= other_val:
                return False
        return True

    def __ge__(self, other_cob) -> bool:
        """Check if self is greater than or equal to value based on comparable seeds.

        All comparable seeds in self must be greater than or equal to those in value
        to return True, otherwise returns False."""
        comparables = self.__dna__._check_and_get_comparables(other_cob)
        for seed in comparables:
            self_val = getattr(self, seed.label)
            other_val = getattr(other_cob, seed.label)
            if self_val < other_val:
                return False
        return True

    def __lt__(self, other_cob) -> bool:
        """Check if self is less than value based on comparable seeds.

        All comparable seeds in self must be less than those in value
        to return True, otherwise returns False."""
        comparables = self.__dna__._check_and_get_comparables(other_cob)
        for seed in comparables:
            self_val = getattr(self, seed.label)
            other_val = getattr(other_cob, seed.label)
            if self_val >= other_val:
                return False
        return True

    def __le__(self, other_cob) -> bool:
        """Check if self is less than or equal to value based on comparable seeds.

        All comparable seeds in self must be less than or equal to those in value
        to return True, otherwise returns False."""
        comparables = self.__dna__._check_and_get_comparables(other_cob)
        for seed in comparables:
            self_val = getattr(self, seed.label)
            other_val = getattr(other_cob, seed.label)
            if self_val > other_val:
                return False
        return True

    def __repr__(self) -> str:
        items = []
        for seed in self.__dna__.seeds:
            items.append(f"{seed.label}={seed.get_value()!r}")
        in_commas = ", ".join(items)
        return f"{type(self).__name__}({in_commas})"
