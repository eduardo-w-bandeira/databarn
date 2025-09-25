from typing import Any
from .trails import fo
from .dna import create_dna
from .exceptions import ConstraintViolationError

# GLOSSARY
# label = grain var name in the cob
# key_name = grain key name in the dict/json output
# value = value dynamically getted from the cob attribute
# primakey = primary key value
# keyring = single primakey or tuple of composite primakeys


class MetaCob(type):
    """Sets the __dna__ attribute for the Cob-model."""

    def __new__(klass, name, bases, dikt):
        new_class = super().__new__(klass, name, bases, dikt)
        new_class.__dna__ = create_dna(new_class)
        return new_class


class Cob(metaclass=MetaCob):
    """The base class for all in-memory data models."""

    def __init__(self, *args, **kwargs):
        """Initializes a Cob-like object.

        - Positional args are assigned to the cob seeds
        in the order they were declared in the Cob-model.
        - Static seed kwargs are assigned by name. If the seed is not
        defined in the cob-model, a NameError is raised.
        - Dynamic seed kwargs are assigned by name. You can do this if you
        didn't define any static seed in the cob-model.

        After all assignments, the `__post_init__` method is called, if defined.

        Args:
            *args: positional args to be assigned to seeds
            **kwargs: keyword args to be assigned to seeds
        """
        ob_dna = self.__dna__(self) # Create an object-level __dna__
        self.__dict__.update(__dna__=ob_dna) # Bypass __setattr__

        seeds = self.__dna__.seeds

        for index, value in enumerate(args):
            seed = seeds[index]
            setattr(self, seed.label, value)

        for label, value in kwargs.items():
            if self.__dna__.dynamic:
                self.__dna__._create_dynamic_grain(label)
            elif label not in self.__dna__.labels:
                raise ConstraintViolationError(fo(f"""
                        Cannot assign '{label}={value}' because the grain
                        '{label}' has not been defined in the model.
                        Since at least one static grain has been defined in
                        the model, dynamic grain assignment is not allowed."""))
            seed = self.__dna__.get_seed(label)
            if seed.wiz_child_model:
                raise ConstraintViolationError(fo(f"""
                    Cannot assign '{label}={value}' because the seed was
                    created by wiz_create_child_barn."""))
            setattr(self, label, value)

        for seed in seeds:
            value = seed.default
            if seed.wiz_child_model:
                # Avoid importing Barn at the top to avoid circular imports
                barn_class = seed.type # This should be Barn
                # Automatically create an empty Barn for the wiz_outer_model_seed
                value = barn_class(seed.wiz_child_model)
            if not seed.was_set:
                setattr(self, seed.label, value)
        if hasattr(self, "__post_init__"):
            self.__post_init__()


    def __setattr__(self, name: str, value: Any):
        """Sets the attribute value, with type and constraint checks for the seed.
        
        Args:
            name (str): The seed name.
            value (Any): The seed value.
        """
        seed = self.__dna__.get_seed(name, None)
        if seed:
            self.__dna__._check_constrains(seed, name, value)
        super().__setattr__(name, value)
        if seed:
            seed.was_set = True
            self.__dna__._set_up_parent_if(seed)

    def __getitem__(self, key: str) -> Any:
        """Access seed values in a dictionary-like way.
        Other attributes are not accessible this way.

        Args:
            key (str): The seed name.
        Returns:
            Any: The seed value.
        """
        seed = self.__dna__.get_seed(key, None)
        if seed is None:
            raise KeyError(f"Grain '{key}' not found in Cob '{type(self).__name__}'.")
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set seed values in a dictionary-like way.
        Other attributes are not settable this way.

        Args:
            key (str): The seed name.
            value (Any): The seed value.
        """
        seed = self.__dna__.get_seed(key, None)
        if seed is None:
            if self.__dna__.dynamic:
                self.__dna__._create_dynamic_grain(key)
            else:
                raise KeyError(f"Grain '{key}' not found in Cob '{type(self).__name__}'.")
        setattr(self, key, value)

    def __contains__(self, key: str) -> bool:
        """Allow use of 'in' keyword to check if a grain label exists in the Cob.

        Args:
            key (str): The grain name.

        Returns:
            bool: True if the seed exists, False otherwise.
        """
        return key in self.__dna__.labels

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
        comparable_seeds = self.__dna__._check_and_get_comparable_seeds(other_cob)
        for seed in comparable_seeds:
            if seed.value != getattr(other_cob, seed.label):
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
        comparable_seeds = self.__dna__._check_and_get_comparable_seeds(other_cob)
        for seed in comparable_seeds:
            self_val = getattr(self, seed.label)
            other_val = getattr(other_cob, seed.label)
            if self_val <= other_val:
                return False
        return True

    def __ge__(self, other_cob) -> bool:
        """Check if self is greater than or equal to value based on comparable seeds.

        All comparable seeds in self must be greater than or equal to those in value
        to return True, otherwise returns False."""
        comparable_seeds = self.__dna__._check_and_get_comparable_seeds(other_cob)
        for seed in comparable_seeds:
            self_val = getattr(self, seed.label)
            other_val = getattr(other_cob, seed.label)
            if self_val < other_val:
                return False
        return True
    
    def __lt__(self, other_cob) -> bool:
        """Check if self is less than value based on comparable seeds.

        All comparable seeds in self must be less than those in value
        to return True, otherwise returns False."""
        comparable_seeds = self.__dna__._check_and_get_comparable_seeds(other_cob)
        for seed in comparable_seeds:
            self_val = getattr(self, seed.label)
            other_val = getattr(other_cob, seed.label)
            if self_val >= other_val:
                return False
        return True

    def __le__(self, other_cob) -> bool:
        """Check if self is less than or equal to value based on comparable seeds.

        All comparable seeds in self must be less than or equal to those in value
        to return True, otherwise returns False."""
        comparable_seeds = self.__dna__._check_and_get_comparable_seeds(other_cob)
        for seed in comparable_seeds:
            self_val = getattr(self, seed.label)
            other_val = getattr(other_cob, seed.label)
            if self_val > other_val:
                return False
        return True

    def __repr__(self) -> str:
        items = []
        for seed in self.__dna__.seeds:
            items.append(f"{seed.label}={seed.value!r}")
        in_commas = ", ".join(items)
        return f"{type(self).__name__}({in_commas})"


