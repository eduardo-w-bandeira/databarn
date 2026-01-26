from collections.abc import MutableSet
from typing import Iterable, Iterator, TypeVar, overload
import re


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

class classmethod_only:
    def __init__(self, method):
        self.method = method

    def __get__(self, instance, owner):
        if instance is not None:
            raise AttributeError("This method can only be called from the class, not an instance.")
        return self.method.__get__(owner, owner)


T = TypeVar("T")

class Catalog(MutableSet[T]):
    """An ordered set that preserves insertion order and supports unhashable elements."""
    
    def __init__(self, iterable: Iterable[T] | None = None):
        self._items: list[T] = []
        if iterable is not None:
            for item in iterable:
                self.add(item)

    def __contains__(self, item: T) -> bool:
        return any(self._equals(existing, item) for existing in self._items)

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def add(self, item: T) -> None:
        if item not in self:
            self._items.append(item)

    def discard(self, item: T) -> None:
        for i, existing in enumerate(self._items):
            if self._equals(existing, item):
                del self._items[i]
                break

    def remove(self, value):
        if value not in self:
            raise KeyError(f"{value} not found in Catalog")
        for i, existing in enumerate(self._items):
            if self._equals(existing, value):
                del self._items[i]
                break

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._items!r})"

    @staticmethod
    def _equals(a: T, b: T) -> bool:
        """Custom equality check to support unhashable types."""
        try:
            return a == b
        except Exception:
            return id(a) == id(b)

    @overload
    def __getitem__(self, index: int) -> T: ...
    @overload
    def __getitem__(self, index: slice) -> list[T]: ...

    def __getitem__(self, index):
        """Support index and slice access."""
        return self._items[index]