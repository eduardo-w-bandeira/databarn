"""
Simple in-memory ORM and data carrier
"""
from typing import Any, Type, List, ValuesView, Tuple

__all__ = ["Field", "Model", "Barn"]


class Field:
    """Represents a field in a Model."""

    def __init__(self, type: Type | Tuple[Type] = object,
                 default: Any = None, primary_key: bool = False,
                 autoincrement: bool = False, frozen: bool = False):
        """
        Args:
            type (type or tuple): The type or tuple of types of the field's value. Defaults to object.
            default (Any): The default value of the field. Defaults to None.
            primary_key (bool): Indicates whether this field is the primary key. Defaults to False.
            autoincrement (bool): If True, Barn will assign an incremental integer number to the field. Defaults to False.
            frozen (bool): If True, the field's value cannot be modified after it has been assigned. Defaults to False.
        """
        self.type = type
        self.default = default
        self.is_pk = primary_key
        self.autoincrement = autoincrement
        self.frozen = frozen


class Meta:
    """Meta class for Model"""

    def __init__(self, parent):
        self.parent = parent
        self.name_field = {}
        self.auto_id = None
        # If primary_key is not provided, auto_id will be used as primary key
        self.pk_name = None
        self.barn = None

    @property
    def pk_value(self):
        if self.pk_name is None:
            return self.auto_id
        return getattr(self.parent, self.pk_name)


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
        super().__setattr__("_meta", Meta(self))  # => self._meta = Meta(self)
        for name, value in self.__class__.__dict__.items():
            if isinstance(value, Field):
                self._meta.name_field[name] = value
                if value.is_pk:
                    self._meta.pk_name = name

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
        """Sets an attribute value, enforcing type checks and checking for frozen attributes.

        Args:
            name (str): The name of the attribute.
            value (Any): The value to be assigned to the attribute.

        Raises:
            AttributeError: If the field is set to frozen and the value is changed after assignment.
            TypeError: If the value type does not match the expected type defined in the Field.
        """
        if name in self._meta.name_field:
            field = self._meta.name_field[name]
            if field.frozen and getattr(self, name) != field:
                msg = (f"Attribute `{name}` cannot be modified to `{value}`, "
                       "since it was defined as frozen.")
                raise AttributeError(msg)
            elif not isinstance(value, field.type) and value != None:
                msg = (f"Type mismatch for attribute '{name}'. "
                       f"Expected {field.type}, got {type(value).__name__}.")
                raise TypeError(msg)
            if field.is_pk and self._meta.barn:
                self._meta.barn._update_pk(getattr(self, name), value)
        super().__setattr__(name, value)

    def __repr__(self) -> str:
        field_values = ', '.join(
            f"{name}={getattr(self, name)}" for name in self._meta.name_field)
        return f"<{self.__class__.__name__}({field_values})>"


class Barn:
    """Manages a collection of objs in an in-memory data structure.

    Attributes:
        _next_auto_id (int): The next available auto_id for primary key generation.
        _pk_obj (dict): A dictionary storing objs by their primary key.

    Methods:
        add(self, obj): Adds a obj (Model) to the Barn.
        get_all(self): Retrieves all objs stored in the Barn.
        get(self, primary_key_value): Retrieves an obj by its primary key value.
        remove(self, obj): Removes a obj from the Barn.
        find_all(self, **kwargs): Finds all objs matching the given criteria.
        find(self, **kwargs): Finds the first obj matching the given criteria.
    """

    def __init__(self):
        self._next_auto_id = 1
        self._pk_obj = {}

    def _assign_autoincrement(self, obj: Model) -> None:
        for name, field in obj._meta.name_field.items():
            if field.autoincrement:
                setattr(obj, name, self._next_auto_id)

    def add(self, obj: Model) -> None:
        """Adds an obj to the Barn. Barn keeps insertion order.

        Args:
            obj (Model): The obj to be added.

        Raises:
            ValueError: If the primary key value is already in use or is None.
        """
        obj._meta.auto_id = self._next_auto_id
        self._assign_autoincrement(obj)
        if obj._meta.pk_value is None:
            raise ValueError("None is not valid as a primary key value.")
        elif obj._meta.pk_value in self._pk_obj:
            raise ValueError(
                f"Primary key {obj._meta.pk_value} already in use.")
        self._next_auto_id += 1
        obj._meta.barn = self
        self._pk_obj[obj._meta.pk_value] = obj

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
        del self._pk_obj[obj._meta.pk_value]
        obj._meta.barn = None
        obj._meta.auto_id = None

    def _matches_criteria(self, obj: Model, **kwargs) -> bool:
        """Checks if an obj matches the given criteria.

        Args:
            obj: The object to check.
            **kwargs: Keyword arguments representing field-value pairs to match.

        Returns:
            bool: True if the obj matches all criteria, False otherwise.
        """
        for field_name, field_value in kwargs.items():
            if getattr(obj, field_name) != field_value:
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
            raise ValueError(f"Primary key {new} already in use.")
        old_pk_obj = self._pk_obj
        self._pk_obj = {}
        for pk, obj in old_pk_obj.items():
            if pk == old:
                pk = new
            self._pk_obj[pk] = obj

    def __len__(self) -> int:
        return len(self._pk_obj)

    def __repr__(self) -> str:
        return f"Barn({len(self)} objs)"
