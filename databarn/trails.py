from collections.abc import Iterable, Iterator, MutableSet
from typing import overload


class Sentinel:
    """Named singleton-like marker object used for special states."""

    def __init__(self, name: str):
        """Initialize a sentinel with a human-readable name."""
        self.name = name

    def __repr__(self) -> str:
        """Return debug representation including sentinel name."""
        return f"<Sentinel: {self.name}>"


def fo(string: str) -> str:
    """Dedents and strips a multi-line string.

    Example:
        raise AttributeError(fo(f'''
                Attribute '{name}' has not been set for this Cob instance,
                or it was deleted.'''))
        Will produce: Attribute 'name' has not been set for this Cob instance, or it was deleted.

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
    """Descriptor that behaves like a property on class and instance access."""

    def __init__(self, method=None) -> None:
        """Store getter callable used for both class and instance lookups."""
        self.method = method

    def __get__(self, ob, owner):
        """Evaluate property against owner class or instance transparently."""
        if ob is None:
            # Class access
            return self.method(owner)
        # Instance access
        return self.method(ob)


class dual_method:
    """Descriptor that binds one method implementation to class or instance."""

    def __init__(self, method) -> None:
        """Store method callable to be dynamically bound on access."""
        self.method = method

    def __get__(self, ob, owner):
        """Return a wrapper bound to the class when ``ob`` is None, else instance."""
        def wrapper(*args, **kwargs):
            abstraction = owner if ob is None else ob
            return self.method(abstraction, *args, **kwargs)
        return wrapper


class classmethod_only:
    """Descriptor like ``classmethod`` but forbidden on instances."""

    def __init__(self, method) -> None:
        """Store class-only callable."""
        self.method = method

    def __get__(self, instance, owner):
        """Bind callable to class and reject instance access."""
        if instance is not None:
            raise AttributeError(
                "This method can only be called from the class, not an instance.")
        return self.method.__get__(owner, owner)


class Catalog[ItemType](MutableSet[ItemType]):
    """An ordered set that preserves insertion order and supports unhashable elements."""

    def __init__(self, iterable: Iterable[ItemType] | None = None):
        """Initialize an ordered set optionally seeded from ``iterable``."""
        self._items: list[ItemType] = []
        if iterable is not None:
            for item in iterable:
                self.add(item)

    def __contains__(self, item: ItemType) -> bool:
        """Return whether an equal item already exists."""
        return any(self._equals(existing, item) for existing in self._items)

    def __iter__(self) -> Iterator[ItemType]:
        """Iterate items in insertion order."""
        return iter(self._items)

    def __len__(self) -> int:
        """Return number of stored items."""
        return len(self._items)

    def add(self, item: ItemType) -> None:
        """Insert ``item`` if not already present."""
        if item not in self:
            self._items.append(item)

    def discard(self, item: ItemType) -> None:
        """Remove ``item`` if present; ignore missing items."""
        for index, existing in enumerate(self._items):
            if self._equals(existing, item):
                del self._items[index]
                break

    def remove(self, item: ItemType) -> None:
        """Remove ``item`` or raise ``KeyError`` if missing."""
        if item not in self:
            raise KeyError(f"{item} not found in Catalog")
        for index, existing in enumerate(self._items):
            if self._equals(existing, item):
                del self._items[index]
                break

    def __repr__(self) -> str:
        """Return repr with ordered item list."""
        return f"{self.__class__.__name__}({self._items!r})"

    @staticmethod
    def _equals(a: ItemType, b: ItemType) -> bool:
        """Custom equality check to support unhashable types."""
        try:
            return a == b
        except Exception:
            return id(a) == id(b)

    @overload
    def __getitem__(self, index: int) -> ItemType: ...
    @overload
    def __getitem__(self, index: slice) -> list[ItemType]: ...

    def __getitem__(self, index: int | slice):
        """Support index and slice access."""
        return self._items[index]
