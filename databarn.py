"""
Simple in-memory data manager and data carrier
"""
from typing import Any, Type, Dict, List, ValuesView
import warnings

__all__ = ["Field", "Model", "Barn"]


class Field:
    """Represents a field in a Model.

    Attributes:
        type (type): The expected type of the field's value. Defaults to object.
        default (Any): The default value of the field. Defaults to None.
        is_pk (bool): Indicates whether this field is the primary key. Defaults to False.
        enforce_type (bool): If True, raises a TypeError when a value of incorrect type is assigned. Defaults to True.
        type_warning (bool): If True and enforce_type is False, issues a warning when a value of incorrect type is assigned. Defaults to True.
    """

    def __init__(self, type: Type = object, default: Any = None, primary_key: bool = False,
                 enforce_type: bool = True, type_warning: bool = True):
        """
        Args:
            type (type, optional): The expected type of the field's value. Defaults to object.
            default (Any, optional): The default value of the field. Defaults to None.
            primary_key (bool, optional): Indicates whether this field is the primary key. Defaults to False.
            enforce_type (bool, optional): If True, raises a TypeError when a value of incorrect type is assigned. Defaults to True.
            type_warning (bool, optional): If True and enforce_type is False, issues a warning when a value of incorrect type is assigned. Defaults to True.
        """
        self.type = type
        self.default = default
        self.is_pk = primary_key
        self.enforce_type = enforce_type
        self.type_warning = type_warning


class Meta:
    pass


class PrimaryKeyNotDefined:
    """Placeholder for undefined primary key."""
    pass


class Model:
    """Represents a table in the in-memory data manager.

    Attributes:
        _meta (Meta): A metadata object.

    Methods:
        __init__(self, *args, **kwargs): Initializes a Model instance with positional and keyword arguments.
        __setattr__(self, name, value): Sets an attribute value, enforcing type checks if specified in the Field definition.
    """

    def __init__(self, *args, **kwargs):
        """
        Args:
            *args: Positional arguments to initialize field values in order of their definition.
            **kwargs: Keyword arguments to initialize field values by name.
        """
        # For preventing unecessary processing in  __setattr__
        super().__setattr__("_meta", Meta())  # self._meta = Meta()
        self._meta.name_field = {}
        self._meta.index = None
        # obj._meta.index is assigned in Barn.add()
        # If primary_key is not provided, Barn will use obj._meta.index as primary_key.
        self._meta.pk = PrimaryKeyNotDefined
        self._meta.barn = None
        for name, value in self.__class__.__dict__.items():
            if isinstance(value, Field):
                self._meta.name_field[name] = value

        for index, value in enumerate(args):
            name = list(self._meta.name_field.keys())[index]
            setattr(self, name, value)

        for name, value in kwargs.items():
            if name not in self._meta.name_field:
                self._meta.name_field[name] = Field()
            setattr(self, name, value)

        for name, field in self._meta.name_field.items():
            if getattr(self, name) == field:
                setattr(self, name, field.default)

    def __setattr__(self, name: str, value: Any):
        """Sets an attribute value, enforcing type checks if specified in the Field definition.

        Args:
            name (str): The name of the attribute.
            value (Any): The value to be assigned to the attribute.

        Raises:
            TypeError: If the value type does not match the expected type defined in the Field and enforce_type is True.
        """
        if name in self._meta.name_field:
            field = self._meta.name_field[name]
            if not isinstance(value, field.type) and value != None:
                msg = (f"Type mismatch for attribute '{name}'. "
                       f"Expected {field.type.__name__}, got {type(value).__name__}.")
                if field.enforce_type:
                    raise TypeError(msg)
                elif field.type_warning:
                    warnings.warn(msg)
            if field.is_pk:
                self._meta.pk = value
                if self._meta.barn:
                    old = getattr(self, name)
                    self._meta.barn._update_pk(old, value)
        super().__setattr__(name, value)

    def __repr__(self) -> str:
        field_values = ', '.join(
            f"{name}={getattr(self, name)}" for name in self._meta.name_field)
        return f"<{self.__class__.__name__}({field_values})>"


class Barn:
    """Manages a collection of objs in an in-memory data structure.

    Attributes:
        _next_index (int): The next available index for primary key generation.
        _data (dict): A dictionary storing objs by their primary key.

    Methods:
        add(self, obj): Adds a obj (Model) to the Barn.
        get_all(self): Retrieves all objs stored in the Barn.
        get(self, primary_key_value): Retrieves an obj by its primary key value.
        remove(self, obj): Removes a obj from the Barn.
        find_all(self, **kwargs): Finds all objs matching the given criteria.
        find(self, **kwargs): Finds the first obj matching the given criteria.
    """

    def __init__(self):
        self._next_index = 0
        self._pk_obj = {}

    def add(self, obj: Model) -> None:
        """Adds an obj to the Barn. Barn keeps insertion order.

        Args:
            obj (Model): The obj to be added.

        Raises:
            ValueError: If the primary key value is already in use.
        """
        pk = obj._meta.pk
        if pk is PrimaryKeyNotDefined:
            pk = self._next_index
            obj._meta.pk = pk
        elif pk in self._pk_obj:
            raise ValueError(f"Primary key {pk} already in use.")
        obj._meta.index = self._next_index
        self._next_index += 1
        obj._meta.barn = self
        self._pk_obj[pk] = obj

    def get_all(self) -> ValuesView[Model]:
        """Orderly retrieves all objs stored in the Barn.

        Returns:
            dict_values: A view object that displays a list of all objs.
        """
        return self._pk_obj.values()

    def get(self, primary_key_value: Any) -> Model:
        """Retrieves an obj by its primary key value.

        Args:
            primary_key_value (Any): The primary key value of the obj.

        Returns:
            obj (Model): The obj, or None if not found.
        """
        return self._pk_obj.get(primary_key_value, None)

    def remove(self, obj: Model) -> None:
        """Removes an obj from the Barn.

        Args:
            obj (Model): The obj to be removed.
        """
        del self._pk_obj[obj._meta.pk]
        obj._meta.barn = None
        obj._meta.index = None

    def _matches_criteria(self, obj: Model, **kwargs) -> bool:
        """Checks if an obj matches the given criteria.

        Args:
            obj: The object to check.
            **kwargs: Keyword arguments representing field-value pairs to match.

        Returns:
            bool: True if the obj matches all criteria, False otherwise.
        """
        for field_name, field_value in kwargs.items():
            if not hasattr(obj, field_name) or getattr(obj, field_name) != field_value:
                return False
        return True

    def find_all(self, **kwargs) -> List[Model]:
        """Finds all objs matching the given criteria.

        Args:
            **kwargs: Keyword arguments representing field-value pairs to match.

        Returns:
            list: A list of objs that match the given criteria.
        """
        results = []
        for obj in self._pk_obj.values():
            if self._matches_criteria(obj, **kwargs):
                results.append(obj)
        return results

    def find(self, **kwargs) -> Model:
        """Finds the first obj matching the given criteria.

        Args:
            **kwargs: Keyword arguments representing field-value pairs to match.

        Returns:
            obj (Model): The first obj that matches the given criteria, or None if no match is found.
        """
        for obj in self._pk_obj.values():
            if self._matches_criteria(obj, **kwargs):
                return obj
        return None

    def _update_pk(self, old: Any, new: Any) -> None:
        if old == new:
            return
        if new in self._pk_obj:
            raise ValueError(f"Primary key {id} already in use.")
        old_pk_obj = self._pk_obj
        self._pk_obj = {}
        for key, value in old_pk_obj.items():
            if key == old:
                key = new
            self._pk_obj[key] = value

    def __len__(self) -> int:
        return len(self._pk_obj)

    def __repr__(self) -> str:
        return f"Barn({len(self)} objs)"
