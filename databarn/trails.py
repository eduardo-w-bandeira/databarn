from collections.abc import Callable
from typing import Any


class Sentinel:
    """Named singleton-like marker object used for special states."""

    def __init__(self, name: str) -> None:
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

    def __init__(self, method: Callable[[Any], Any] | None = None) -> None:
        """Store getter callable used for both class and instance lookups."""
        self.method = method

    def __get__(self, ob: Any, owner: type[Any]) -> Any:
        """Evaluate property against owner class or instance transparently."""
        if ob is None:
            # Class access
            return self.method(owner)
        # Instance access
        return self.method(ob)


class dual_method:
    """Descriptor that binds one method implementation to class or instance."""

    def __init__(self, method: Callable[[Any, ...], Any]) -> None:
        """Store method callable to be dynamically bound on access."""
        self.method = method

    def __get__(self, ob: Any, owner: type[Any]) -> Callable[..., Any]:
        """Return a wrapper bound to the class when ``ob`` is None, else instance."""
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            abstraction = owner if ob is None else ob
            return self.method(abstraction, *args, **kwargs)
        return wrapper


class classmethod_only:
    """Descriptor like ``classmethod`` but forbidden on instances."""

    def __init__(self, method: Callable[[type[Any]], Any]) -> None:
        """Store class-only callable."""
        self.method = method

    def __get__(self, instance: Any | None, owner: type[Any]) -> Callable[..., Any]:
        if instance is not None:
            raise AttributeError(
                "This method can only be called from the class, not an instance.")
        return self.method.__get__(owner, owner)
