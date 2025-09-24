from typing import Any
from .trails import fo
from .dna import create_dna
from .exceptions import ConsistencyError

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

        - Positional args are assigned to the cob flakes
        in the order they were declared in the Cob-model.
        - Static flake kwargs are assigned by name. If the flake is not
        defined in the cob-model, a NameError is raised.
        - Dynamic flake kwargs are assigned by name. You can do this if you
        didn't define any static flake in the cob-model.

        After all assignments, the `__post_init__` method is called, if defined.

        Args:
            *args: positional args to be assigned to flakes
            **kwargs: keyword args to be assigned to flakes
        """
        ob_dna = self.__dna__(self) # Create an object-level __dna__
        self.__dict__.update(__dna__=ob_dna) # Bypass __setattr__

        flakes = self.__dna__.flakes

        for index, value in enumerate(args):
            flake = flakes[index]
            setattr(self, flake.label, value)

        for label, value in kwargs.items():
            if self.__dna__.dynamic:
                self.__dna__._create_dynamic_grain(label)
            elif label not in self.__dna__.labels:
                raise ConsistencyError(fo(f"""
                        Cannot assign '{label}={value}' because the grain
                        '{label}' has not been defined in the model.
                        Since at least one static grain has been defined in
                        the model, dynamic grain assignment is not allowed."""))
            flake = self.__dna__.get_flake(label)
            if flake.wiz_child_model:
                raise ConsistencyError(fo(f"""
                    Cannot assign '{label}={value}' because the flake was
                    created by wiz_create_child_barn."""))
            setattr(self, label, value)

        for flake in flakes:
            value = flake.default
            if flake.wiz_child_model:
                # Avoid importing Barn at the top to avoid circular imports
                barn_class = flake.type # This should be Barn
                # Automatically create an empty Barn for the wiz_outer_model_flake
                value = barn_class(flake.wiz_child_model)
            if not flake.was_set:
                setattr(self, flake.label, value)
        if hasattr(self, "__post_init__"):
            self.__post_init__()


    def __setattr__(self, name: str, value: Any):
        """Sets the attribute value, with type and constraint checks for the flake.
        
        Args:
            name (str): The flake name.
            value (Any): The flake value.
        """
        flake = self.__dna__.get_flake(name, None)
        if flake:
            self.__dna__._check_and_set_up(flake, name, value)
        super().__setattr__(name, value)
        if flake:
            flake.was_set = True
            self.__dna__._set_up_parent_if(flake)

    def __getitem__(self, key: str) -> Any:
        """Access flake values in a dictionary-like way.
        Other attributes are not accessible this way.

        Args:
            key (str): The flake name.
        Returns:
            Any: The flake value.
        """
        flake = self.__dna__.get_flake(key, None)
        if flake is None:
            raise KeyError(f"Grain '{key}' not found in Cob '{type(self).__name__}'.")
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Set flake values in a dictionary-like way.
        Other attributes are not settable this way.

        Args:
            key (str): The flake name.
            value (Any): The flake value.
        """
        flake = self.__dna__.get_flake(key, None)
        if flake is None:
            raise KeyError(f"Grain '{key}' not found in Cob '{type(self).__name__}'.")
        setattr(self, key, value)

    def __contains__(self, key: str) -> bool:
        """Allow use of 'in' keyword to check if a grain label exists in the Cob.

        Args:
            key (str): The grain name.

        Returns:
            bool: True if the flake exists, False otherwise.
        """
        return key in self.__dna__.labels

    def __eq__(self, other_cob: Any) -> bool:
        """Check equality between two Cob objects based on comparable grains.

        As a rule, comparisons require at least the definition of one comparable grain.
        However, there's an exception: if both objects are the same, they are considered equal.
        In all other cases, the comparison is based on comparable flakes.

        All comparable flakes must be equal for the objects to be considered equal."""
        if self is other_cob:
            # As a rule, comparisons require at least the definition of a comparable grain,
            # But if they are the same object, they are equal anyway.
            return True 
        comparable_flakes = self.__dna__._check_and_get_comparable_flakes(other_cob)
        for flake in comparable_flakes:
            if flake.value != getattr(other_cob, flake.label):
                return False
        return True

    def __ne__(self, other_cob) -> bool:
        """Check inequality between two Cob objects based on comparable flakes."""
        return not self.__eq__(other_cob)

    def __gt__(self, other_cob) -> bool:
        """Check if self is greater than value based on comparable flakes.
        
        All comparable flakes in self must be greater than those in value
        to return True, otherwise returns False.
        """
        comparable_flakes = self.__dna__._check_and_get_comparable_flakes(other_cob)
        for flake in comparable_flakes:
            self_val = getattr(self, flake.label)
            other_val = getattr(other_cob, flake.label)
            if self_val <= other_val:
                return False
        return True

    def __ge__(self, other_cob) -> bool:
        """Check if self is greater than or equal to value based on comparable flakes.

        All comparable flakes in self must be greater than or equal to those in value
        to return True, otherwise returns False."""
        comparable_flakes = self.__dna__._check_and_get_comparable_flakes(other_cob)
        for flake in comparable_flakes:
            self_val = getattr(self, flake.label)
            other_val = getattr(other_cob, flake.label)
            if self_val < other_val:
                return False
        return True
    
    def __lt__(self, other_cob) -> bool:
        """Check if self is less than value based on comparable flakes.

        All comparable flakes in self must be less than those in value
        to return True, otherwise returns False."""
        comparable_flakes = self.__dna__._check_and_get_comparable_flakes(other_cob)
        for flake in comparable_flakes:
            self_val = getattr(self, flake.label)
            other_val = getattr(other_cob, flake.label)
            if self_val >= other_val:
                return False
        return True

    def __le__(self, other_cob) -> bool:
        """Check if self is less than or equal to value based on comparable flakes.

        All comparable flakes in self must be less than or equal to those in value
        to return True, otherwise returns False."""
        comparable_flakes = self.__dna__._check_and_get_comparable_flakes(other_cob)
        for flake in comparable_flakes:
            self_val = getattr(self, flake.label)
            other_val = getattr(other_cob, flake.label)
            if self_val > other_val:
                return False
        return True

    def __repr__(self) -> str:
        items = []
        for flake in self.__dna__.flakes:
            items.append(f"{flake.label}={flake.value!r}")
        in_commas = ", ".join(items)
        return f"{type(self).__name__}({in_commas})"


