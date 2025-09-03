from __future__ import annotations
from typing import Any, Iterator, Type

from .cob import Cob


class Barn:
    """In-memory storage for cob-like objects.

    Provides methods to find and retrieve
    Cob objects based on their keys or grains.
    """
    parent_cob: Cob | None = None

    def __init__(self, model: Type[Cob] = Cob):
        """Initialize the Barn.

        Args:
            model: The Cob-like class whose objects will be stored in this Barn.
        """
        # issubclass also returns True if the subclass is the parent class
        if not issubclass(model, Cob):
            raise TypeError(
                f"Expected a Cob-like class for the model arg, but got {model}.")
        self.model = model
        self._next_autoid = 1
        self._keyring_cob_map: dict = {}

    def _assign_auto(self, cob: Cob, value: int) -> None:
        """Assign an auto grain value to the cob, if applicable.

        Args:
            cob: The cob whose auto grains should be assigned.
            value: The value to assign to the auto grains.
        """
        for grain in cob.__dna__.label_grain_map.values():
            if grain.auto and grain.value is None:
                cob.__dict__[grain.label] = value
                grain.was_set = True

    def _check_keyring(self, keyring: Any | tuple) -> bool:
        """Check if the key(s) is unique and not None.

        Args:
            keyring: The key or tuple of composite keys.

        Returns:
            True if the keyring is valid.

        Raises:
            KeyError: If the keyring is None or already in use.
        """
        if self.model.__dna__.is_compos_key:
            has_none = any(key is None for key in keyring)
            if has_none:
                raise KeyError("None is not valid as key.")
        elif keyring is None:
            raise KeyError("None is not valid as key.")
        if keyring in self._keyring_cob_map:
            raise KeyError(
                f"Key {keyring} already in use.")
        return True

    def _check_grains_for_uniqueness(self, grains: list) -> bool:
        """Check uniqueness of the unique-type grains against barn cobs.

        Args:
            unique_type_grains: The list of unique-type grains to check.

        Returns:
            True if the grain is unique.

        Raises:
            ValueError: If the value is already in use for that particular grain.
                None value is allowed.
        """
        for cob in self._keyring_cob_map.values():
            for grain in grains:
                if grain.value == getattr(cob, grain.label):
                    raise ValueError(
                        f"Grain {grain.label}={grain.value} is not unique.")
        return True

    def _check_uniqueness_by_cob(self, cob: Cob) -> bool:
        """Check uniqueness of the unique-type grains against the stored cobs.

        Args:
            cob: The cob whose unique grains should be checked.

        Returns:
            True if the grain is unique.

        Raises:
            ValueError: If the value is already in use for that particular grain.
                None value is allowed.
        """
        uniques: list = []
        for grain in cob.__dna__.label_grain_map.values():
            if grain.unique:
                uniques.append(grain)
        if not uniques:  # Prevent unnecessary processing
            return True
        return self._check_grains_for_uniqueness(uniques)

    def _check_uniqueness_by_label(self, label: str, value: Any) -> bool:
        """Check uniqueness of the unique-type grains against the stored cobs.

        Args:
            label: The label of the grain to check.
            value: The value of the grain to check.

        Returns:
            True if the grain is unique.

        Raises:
            ValueError: If the value is already in use for that particular grain.
                None value is allowed.
        """
        grain = Cob(label=label, value=value)
        return self._check_grains_for_uniqueness([grain])

    def append(self, cob: Cob) -> None:
        """Add a cob to the Barn in the order they were added.

        Args:
            cob: The cob-like object to add. The cob must be
                of the same type as the model defined for this Barn.

        Raises:
            TypeError: If the cob is not of the same type as the model
                defined for this Barn.
            KeyError: If the key is in use or is None.
            ValueError: If the a unique grain is not unique.
        """
        if not isinstance(cob, self.model):
            raise TypeError(
                (f"Expected cob {self.model} for the cob arg, but got {type(cob)}. "
                 "The provided cob is of a different type than the "
                 "model defined for this Barn."))
        if cob.__dna__.autoid is None:
            cob.__dna__.autoid = self._next_autoid
        self._assign_auto(cob, self._next_autoid)
        self._next_autoid += 1
        cob.__dna__.barns.add(self)
        self._check_keyring(cob.__dna__.keyring)
        self._check_uniqueness_by_cob(cob)
        self._keyring_cob_map[cob.__dna__.keyring] = cob
        if self.parent_cob:
            cob.__dna__.parent = self.parent_cob

    def add_all(self, *cobs: Cob) -> Barn:
        """Append multiple cobs to the Barn.

        Args:
            *cobs: The cob-like objects to add. Each cob must be
                of the same type as the model defined for this Barn.
        
        Returns:
            Barn: The current Barn instance, to allow method chaining.
        """
        for cob in cobs:
            self.append(cob)
        return self

    def _get_keyring(self, *keys, **labeled_keys) -> tuple[Any] | Any:
        """Return a keyring as a tuple of keys or a single key.

        You can provide either positional args or kwargs, but not both.

        Raises:
            SyntaxError: If nothing was provided, or
                both positional keys and labeled_keys were provided, or
                the number of keys does not match the key grains.
        """

        if not keys and not labeled_keys:
            raise SyntaxError("No keys or labeled_keys were provided.")
        if keys and labeled_keys:
            raise SyntaxError("Both positional keys and labeled_keys "
                              "cannot be provided together.")
        if keys:
            if self.model.__dna__.keyring_len != (keys_len := len(keys)):
                raise SyntaxError(f"Expected {self.model.__dna__.keyring_len} keys, "
                                  f"but got {keys_len}.")
            keyring = keys[0] if keys_len == 1 else keys
        else:
            if self.model.__dna__.dynamic:
                raise SyntaxError(
                    "To use labeled_keys, the provided model for "
                    f"{self.__name__} cannot be dynamic.")
            if self.model.__dna__.keyring_len != len(labeled_keys):
                raise SyntaxError(f"Expected {self.model.__dna__.keyring_len} labeled_keys, "
                                  f"got {len(labeled_keys)} instead.")
            key_lst = [labeled_keys[grain.label]
                       for grain in self.model.__dna__.key_grains]
            keyring = tuple(key_lst)
        return keyring

    def get(self, *keys, **labeled_keys) -> Cob | None:
        """Return a cob from the Barn, given its key or labeled_keys.

        Raises:
            SyntaxError: If nothing was provided, or
                both positional keys and labeled_keys were provided, or
                the number of keys does not match the key grains.

        Returns:
            The cob associated with the key(s), or None if not found.
        """
        keyring = self._get_keyring(*keys, **labeled_keys)
        return self._keyring_cob_map.get(keyring, None)

    def remove(self, cob: Cob) -> None:
        """Remove a cob from the Barn.

        Args:
            cob: The cob to remove
        """
        del self._keyring_cob_map[cob.__dna__.keyring]
        cob.__dna__.barns.discard(self)

    def _matches_criteria(self, cob: Cob, **labeled_values) -> bool:
        """Check if a cob matches the given criteria.

        Args:
            cob: The cob to check
            **labeled_values: The criteria to match

        Returns:
            bool: True if the cob matches the criteria, False otherwise
        """
        for label, value in labeled_values.items():
            if getattr(cob, label) != value:
                return False
        return True

    def find_all(self, **labeled_values) -> Barn:
        """Find all cobs in the Barn that match the given criteria.

        Args:
            **labeled_values: The criteria to match

        Returns:
            Barn: A Barn containing all cobs that match the criteria
        """
        results = Barn(self.model)
        for cob in self._keyring_cob_map.values():
            if self._matches_criteria(cob, **labeled_values):
                results.append(cob)
        return results

    def find(self, **labeled_values) -> Cob:
        """Find the first cob in the Barn that matches the given criteria.

        Args:
            **labeled_values: grain_label=value used as the criteria to match

        Returns:
            Cob: The first cob that matches the criteria, or None not found.
        """
        for cob in self._keyring_cob_map.values():
            if self._matches_criteria(cob, **labeled_values):
                return cob
        return None

    def has_key(self, *keys, **labeled_keys) -> bool:
        """Checks if the provided key(s) is(are) in the Barn."""
        keyring = self._get_keyring(*keys, **labeled_keys)
        return keyring in self._keyring_cob_map

    def __len__(self) -> int:
        """Return the number of cobs in the Barn.

        Returns:
            int: The number of cobs in the Barn.
        """
        return len(self._keyring_cob_map)

    def __repr__(self) -> str:
        length = len(self)
        word = "cob" if length == 1 else "cobs"
        return f"{self.__class__.__name__}({length} {word})"

    def __contains__(self, cob: Cob) -> bool:
        """Check if a cob is in the Barn.

        Args:
            cob: Cob to check for membership

        Returns:
            bool: True if the cob is in the Barn, False otherwise
        """
        return cob in self._keyring_cob_map.values()

    def __getitem__(self, index: int | slice) -> Cob | Barn:
        """Get a cob or a slice of cobs from the Barn.

        Args:
            index: int or slice of the cob(s) to retrieve

        Returns:
            cob or barn: The retrieved cob(s)

        Raises:
            IndexError: If the index is not valid
        """
        cob_or_cobs = list(self._keyring_cob_map.values())[index]
        if type(index) is int:
            return cob_or_cobs
        elif type(index) is slice:
            results = Barn(self.model)
            [results.append(cob) for cob in cob_or_cobs]
            return results
        raise IndexError("Invalid index")

    def __iter__(self) -> Iterator[Cob]:
        """Iterate over the cobs in the Barn.

        Ex.: `for cob in barn: print(cob)`

        Yields:
            Cob: Each cob in the Barn, in the order they were added.
        """
        for cob in self._keyring_cob_map.values():
            yield cob

    def _set_parent_cob(self, parent_cob: Cob) -> None:
        """Set the parent cob for this barn and its child cobs."""
        self.parent_cob = parent_cob
        for cob in self._keyring_cob_map.values():
            cob.__dna__.parent = parent_cob