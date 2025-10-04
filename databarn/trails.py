import re
from typing import Iterable, Iterator, Any

class MissingArg:
    """A unique sentinel object to detect missing values."""

    def __repr__(self):
        return "<{self.__class__.__name__}>"

MISSING_ARG = MissingArg()

class NotSet:
    """A unique sentinel object to detect not-set values."""

    def __repr__(self):
        return "<{self.__class__.__name__}>"

NOT_SET = NotSet()


def pascal_to_underscore(name: str) -> str:
    """Converts a PascalCase name to underscore_case.
    Args:
        name (str): The PascalCase name to convert.
    Returns:
        str: The converted underscore_case name.
    """
    # Insert underscore before each capital letter (except the first one)
    # and convert the entire string to lowercase
    underscore = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    return underscore


def fo(string: str):
    """Dedents and strips a multi-line string.

    Args:
        string (str): The multi-line string to format.

    Returns:
        str: The formatted string.
    """
    string = string.replace("\n", " ").strip()
    new_str = ""
    for char in string:
        if char.isspace():
            char = " "
        new_str += char
    while "  " in new_str:
        new_str = new_str.replace("  ", " ")
    return new_str


class dual_property:
    def __init__(self, method=None):
        self.method = method

    def __get__(self, ob, owner):
        if ob is None:
            # Class access
            return self.method(owner)
        # Instance access
        return self.method(ob)


class dual_method:
    def __init__(self, method):
        self.method = method

    def __get__(self, ob, owner):
        def wrapper(*args, **kwargs):
            abstraction = owner if ob is None else ob
            return self.method(abstraction, *args, **kwargs)
        return wrapper

# class class_property(property):
#     """A decorator that behaves like @property but for classmethods.
#     Usage:
#         class MyClass:
#             _value = 42

#             @class_property
#             def value(cls):
#                 return cls._value
#     """

#     def __get__(self, ob, klass):
#         return self.fget(klass)


class Catalog:
    """An ordered set that preserves insertion order."""
    
    def __init__(self, iterable: Iterable | None = None) -> None:
        self._items: dict[Any, None] = {}
        if iterable is not None:
            for item in iterable:
                self.add(item)
    
    def add(self, item: Any) -> None:
        """Add an item to the catalog."""
        self._items[item] = None
    
    def check_and_add(self, item: Any) -> bool:
        if item in self._items:
            raise ValueError(f"Item '{item}' already exists in {type(self).__name__}.")
        self._items[item] = None

    def remove(self, item: Any) -> None:
        """Remove an item if present; do nothing if absent."""
        self._items.pop(item, None)
    
    def check_and_remove(self, item: Any) -> None:
        """Remove an item; raise KeyError if not present."""
        if item not in self._items:
            raise KeyError(f"Item '{item}' not found in {type(self).__name__}.")
        del self._items[item]

    def __contains__(self, item: Any) -> bool:
        return item in self._items
    
    def __iter__(self) -> Iterator[Any]:
        return iter(self._items)
    
    def __len__(self) -> int:
        return len(self._items)
    
    def __repr__(self) -> str:
        sep_items = ", ".join(list(self._items.keys()))
        return f"Catalog({sep_items})"
    
    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Catalog):
            return NotImplemented
        return list(self._items) == list(other._items)
    
    def __getitem__(self, index: int | slice) -> Any | list[Any]:
        """Get the element at a specific position (supports indexing and slicing)."""
        items = list(self._items.keys())
        return items[index]
    
    # def clear(self) -> None:
    #     """Remove all items."""
    #     self._items.clear()
    
    def to_list(self) -> list[Any]:
        """Return all items as a list."""
        return list(self._items.keys())
