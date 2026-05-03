from collections.abc import Iterable, Iterator, MutableSet
from typing import overload


class Sentinel:
    """Named singleton-like marker object used for special states."""

    def __init__(self, name: str):
        """Initialize a sentinel with a human-readable name."""
        self.name = name

    def __repr__(self) -> str:
        """Return debug representation including sentinel name."""
        return f"<{self.name}>"


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
    return " ".join(string.split())


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
