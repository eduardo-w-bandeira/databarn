from typing import Any
import copy
from .trails import fo
from .dna import ObDna
from .exceptions import ConsistencyError

# GLOSSARY
# label = sprout var name in the cob
# key_name = sprout key name in the dict/json output
# value = value dynamically getted from the cob attribute
# primakey = primary key value
# keyring = single primakey or tuple of composite primakeys


class MetaCob(type):
    """Sets the __dna__ attribute for the Cob-model."""

    def __new__(klass, name, bases, dikt):
        new_class = super().__new__(klass, name, bases, dikt)
        new_class.__dna__ = ObDna(new_class)
        return new_class


class Cob(metaclass=MetaCob):
    """The base class for all in-memory data models."""

    def __init__(self, *args, **kwargs):
        """Initializes a Cob-like object.

        - Positional args are assigned to the cob sprouts
        in the order they were declared in the Cob-model.
        - Static sprout kwargs are assigned by name. If the sprout is not
        defined in the cob-model, a NameError is raised.
        - Dynamic sprout kwargs are assigned by name. You can do this if you
        didn't define any static sprout in the cob-model.

        After all assignments, the `__post_init__` method is called, if defined.

        Args:
            *args: positional args to be assigned to sprouts
            **kwargs: keyword args to be assigned to sprouts
        """
        ob_dna = self.__dna__(self) # Create an object-level __dna__
        self.__dict__.update(__dna__=ob_dna) # Bypass __setattr__

        sprouts = self.__dna__.sprouts

        for index, value in enumerate(args):
            sprout = sprouts[index]
            setattr(self, sprout.label, value)

        for label, value in kwargs.items():
            if self.__dna__.dynamic:
                self.__dna__._create_dynamic_sprout(label)
            elif label not in self.__dna__.labels:
                raise ConsistencyError(fo(f"""
                        Cannot assign '{label}={value}' because the sprout
                        '{label}' has not been defined in the Cob-model.
                        Since at least one static sprout has been defined in
                        the Cob-model, dynamic sprout assignment is not allowed."""))
            sprout = self.__dna__.get_sprout(label)
            if sprout.wiz_child_model:
                raise ConsistencyError(fo(f"""
                    Cannot assign '{label}={value}' because the sprout was
                    created by wiz_create_child_barn."""))
            setattr(self, label, value)

        for sprout in sprouts:
            value = sprout.default
            if sprout.wiz_child_model:
                # Avoid importing Barn at the top to avoid circular imports
                barn_class = sprout.type # This should be Barn
                # Automatically create an empty Barn for the wiz_outer_model_sprout
                value = barn_class(sprout.wiz_child_model)
            if not sprout.was_set:
                setattr(self, sprout.label, value)
        if hasattr(self, "__post_init__"):
            self.__post_init__()


    def __setattr__(self, name: str, value: Any):
        """Sets the attribute value, with type and constraint checks for the sprout.
        
        Args:
            name (str): The sprout name.
            value (Any): The sprout value.
        """
        sprout = self.__dna__.label_sprout_map.get(name, None)
        if sprout:
            self.__dna__._check_and_set_up(sprout, name, value)
        super().__setattr__(name, value)
        if sprout:
            sprout.was_set = True
            self.__dna__._set_up_parent_if(sprout)

    def __getitem__(self, key: str) -> Any:
        """Access sprout values in a dictionary-like way.
        Other attributes are not accessible this way.

        Args:
            key (str): The sprout name.
        Returns:
            Any: The sprout value.
        """
        sprout = self.__dna__.label_sprout_map.get(key, None)
        if sprout is None:
            raise KeyError(f"Grain '{key}' not found in Cob '{type(self).__name__}'.")
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set sprout values in a dictionary-like way.
        Other attributes are not settable this way.

        Args:
            key (str): The sprout name.
            value (Any): The sprout value.
        """
        sprout = self.__dna__.label_sprout_map.get(key, None)
        if sprout is None:
            raise KeyError(f"Grain '{key}' not found in Cob '{type(self).__name__}'.")
        setattr(self, key, value)

    def __contains__(self, key: str) -> bool:
        """Allow use of 'in' keyword to check if a sprout label exists in the Cob.

        Args:
            key (str): The sprout name.

        Returns:
            bool: True if the sprout exists, False otherwise.
        """
        return key in self.__dna__.label_sprout_map

    def __eq__(self, other_cob: Any) -> bool:
        """Check equality between two Cob objects based on comparable sprouts.

        As a rule, comparisons require at least the definition of one comparable sprout.
        However, there's an exception: if both objects are the same, they are considered equal.
        In all other cases, the comparison is based on comparable sprouts.

        All comparable sprouts must be equal for the objects to be considered equal."""
        if self is other_cob:
            # As a rule, comparisons require at least the definition of a comparable sprout,
            # But if they are the same object, they are equal anyway.
            return True 
        comparable_sprouts = self.__dna__._check_and_get_comparable_sprouts(other_cob)
        for sprout in comparable_sprouts:
            if sprout.value != getattr(other_cob, sprout.label):
                return False
        return True

    def __ne__(self, other_cob) -> bool:
        """Check inequality between two Cob objects based on comparable sprouts."""
        return not self.__eq__(other_cob)

    def __gt__(self, other_cob) -> bool:
        """Check if self is greater than value based on comparable sprouts.
        
        All comparable sprouts in self must be greater than those in value
        to return True, otherwise returns False.
        """
        comparable_sprouts = self.__dna__._check_and_get_comparable_sprouts(other_cob)
        for sprout in comparable_sprouts:
            self_val = getattr(self, sprout.label)
            other_val = getattr(other_cob, sprout.label)
            if self_val <= other_val:
                return False
        return True

    def __ge__(self, other_cob) -> bool:
        """Check if self is greater than or equal to value based on comparable sprouts.

        All comparable sprouts in self must be greater than or equal to those in value
        to return True, otherwise returns False."""
        comparable_sprouts = self.__dna__._check_and_get_comparable_sprouts(other_cob)
        for sprout in comparable_sprouts:
            self_val = getattr(self, sprout.label)
            other_val = getattr(other_cob, sprout.label)
            if self_val < other_val:
                return False
        return True
    
    def __lt__(self, other_cob) -> bool:
        """Check if self is less than value based on comparable sprouts.

        All comparable sprouts in self must be less than those in value
        to return True, otherwise returns False."""
        comparable_sprouts = self.__dna__._check_and_get_comparable_sprouts(other_cob)
        for sprout in comparable_sprouts:
            self_val = getattr(self, sprout.label)
            other_val = getattr(other_cob, sprout.label)
            if self_val >= other_val:
                return False
        return True

    def __le__(self, other_cob) -> bool:
        """Check if self is less than or equal to value based on comparable sprouts.

        All comparable sprouts in self must be less than or equal to those in value
        to return True, otherwise returns False."""
        comparable_sprouts = self.__dna__._check_and_get_comparable_sprouts(other_cob)
        for sprout in comparable_sprouts:
            self_val = getattr(self, sprout.label)
            other_val = getattr(other_cob, sprout.label)
            if self_val > other_val:
                return False
        return True

    def __repr__(self) -> str:
        items = []
        for sprout in self.__dna__.sprouts:
            items.append(f"{sprout.label}={sprout.value!r}")
        in_commas = ", ".join(items)
        return f"{type(self).__name__}({in_commas})"


