from typing import Any, Iterator, Type

from .seed import Seed
from .field import Field


class Barn:
    """In-memory storage for seed-like objects.

    Provides methods to find and retrieve
    Seed objects based on their keys or fields.
    """

    def __init__(self, seed_model: Type[Seed] = Seed):
        # issubclass also returns True if the subclass is the parent class
        """Initialize the Barn.

        Args:
            seed_model: The Seed-like class whose objects will be stored in this Barn.
        """
        if not issubclass(seed_model, Seed):
            raise TypeError(
                f"Expected a Seed-like class for the seed_model arg, but got {seed_model}.")
        self.seed_model = seed_model
        self._dna = self.seed_model.__dna__
        self._next_autoid = 1
        self._keyring_seed_map: dict = {}

    def _assign_auto(self, seed: Seed, id: int) -> None:
        """Assign an auto field value to the seed, if applicable.

        Args:
            seed: The seed whose auto fields should be assigned.
            id: The value to assign to the auto fields.
        """
        for field in seed.__dna__.label_field_map.values():
            if field.auto and field.value is None:
                seed.__dict__[field.label] = id
                field.was_set = True

    def _validate_keyring(self, keyring: Any | tuple) -> bool:
        """Check if the key(s) is unique and not None.

        Args:
            keyring: The key or tuple of composite keys.

        Returns:
            True if the keyring is valid.

        Raises:
            KeyError: If the keyring is None or already in use.
        """
        if self._dna.is_comp_key:
            has_none = any(key is None for key in keyring)
            if has_none:
                raise KeyError("None is not valid as key.")
        elif keyring is None:
            raise KeyError("None is not valid as key.")
        if keyring in self._keyring_seed_map:
            raise KeyError(
                f"Key {keyring} already in use.")
        return True

    def append(self, seed: Seed) -> None:
        """Add a seed to the Barn in the order they were added.

        Args:
            seed: The seed-like object to add. The seed must be
                of the same type as the model defined for this Barn.

        Raises:
            TypeError: If the seed is not of the same type as the model
                defined for this Barn.
            KeyError: If the key is not unique or is None.
        """
        if not isinstance(seed, self.seed_model):
            raise TypeError(
                (f"Expected seed {self.seed_model} for the seed arg, but got {type(seed)}. "
                 "The provided seed is of a different type than the "
                 "model defined for this Barn."))
        if seed.__dna__.autoid is None:
            seed.__dna__.autoid = self._next_autoid
        self._assign_auto(seed, self._next_autoid)
        self._next_autoid += 1
        seed.__dna__.barns.add(self)
        self._validate_keyring(seed.__dna__.keyring)
        self._keyring_seed_map[seed.__dna__.keyring] = seed

    def _get_keyring(self, *keys, **labeled_keys) -> tuple[Any] | Any:
        """Return a keyring as a tuple of keys or a single key.

        You can provide either positional args or kwargs, but not both.

        Raises:
            SyntaxError: If nothing was provided, or
                both positional keys and labeled_keys were provided, or
                the number of keys does not match the key fields.
        """

        if not keys and not labeled_keys:
            raise SyntaxError("No keys or labeled_keys were provided.")
        if keys and labeled_keys:
            raise SyntaxError("Both positional keys and labeled_keys "
                              "cannot be provided together.")
        if keys:
            if self._dna.keyring_len != (keys_len := len(keys)):
                raise SyntaxError(f"Expected {self._dna.keyring_len} keys, "
                                  f"but got {keys_len}.")
            keyring = keys[0] if keys_len == 1 else keys
        else:
            if self._dna.dynamic:
                raise SyntaxError(
                    "To use labeled_keys, the provided seed_model for "
                    f"{self.__name__} cannot be dynamic.")
            if self._dna.keyring_len != len(labeled_keys):
                raise SyntaxError(f"Expected {self._dna.keyring_len} labeled_keys, "
                                  f"got {len(labeled_keys)} instead.")
            key_lst = [labeled_keys[field.label]
                       for field in self._dna.key_fields]
            keyring = tuple(key_lst)
        return keyring

    def get(self, *keys, **labeled_keys) -> Seed | None:
        """Return a seed from the Barn, given its key or labeled_keys.

        Raises:
            SyntaxError: If nothing was provided, or
                both positional keys and labeled_keys were provided, or
                the number of keys does not match the key fields.

        Returns:
            Seed | None: The seed associated with the key(s), or None if not found.
        """
        keyring = self._get_keyring(*keys, **labeled_keys)
        return self._keyring_seed_map.get(keyring, None)

    def remove(self, seed: Seed) -> None:
        """Remove a seed from the Barn.

        Args:
            seed: The seed to remove
        """
        del self._keyring_seed_map[seed.__dna__.keyring]
        seed.__dna__.barns.discard(self)

    def _matches_criteria(self, seed: Seed, **labeled_values) -> bool:
        """Check if a seed matches the given criteria.

        Args:
            seed: The seed to check
            **labeled_values: The criteria to match

        Returns:
            bool: True if the seed matches the criteria, False otherwise
        """
        for label, value in labeled_values.items():
            if not hasattr(seed, label) or getattr(seed, label) != value:
                return False
        return True

    def find_all(self, **labeled_values) -> "Results":
        """Find all seeds in the Barn that match the given criteria.

        Args:
            **labeled_values: The criteria to match

        Returns:
            Results: A Results containing all seeds that match the criteria
        """
        results = Results(self.seed_model)
        for seed in self._keyring_seed_map.values():
            if self._matches_criteria(seed, **labeled_values):
                results.append(seed)
        return results

    def find(self, **labeled_values) -> Seed:
        """Find the first seed in the Barn that matches the given criteria.

        Args:
            **labeled_values: field_label=value used as the criteria to match

        Returns:
            Seed: The first seed that matches the criteria, or None not found.
        """
        for seed in self._keyring_seed_map.values():
            if self._matches_criteria(seed, **labeled_values):
                return seed
        return None

    def _update_key(self, seed: Seed, key_label: str, new_key: Any) -> None:
        """Update the keyring of a seed in the Barn.

        Args:
            seed: The seed whose keyring needs to be updated
            key_label: The name of the key to update
            new_key: The new key

        This method will update the keyring of the seed and
        reindex the seed in the Barn. If the key is not unique or
        is None, a KeyError is raised.
        """
        old_key = getattr(seed, key_label)
        if old_key == new_key:  # Prevent unecessary processing
            return
        new_keyring = new_key
        if seed.__dna__.is_comp_key:
            keys = []
            for field in seed.__dna__.key_fields:
                key = field.value
                if field.label == key_label:
                    key = new_key
                keys.append(key)
            new_keyring = tuple(keys)
        self._validate_keyring(new_keyring)
        old_keyring_seed_map = self._keyring_seed_map
        self._keyring_seed_map = {}
        for keyring, seed in old_keyring_seed_map.items():
            if keyring == seed.__dna__.keyring:
                keyring = new_keyring
            self._keyring_seed_map[keyring] = seed

    def has_key(self, *keys, **labeled_keys) -> bool:
        """Checks if the provided key(s) is(are) in the Barn."""
        keyring = self._get_keyring(*keys, **labeled_keys)
        return keyring in self._keyring_seed_map

    def field_values(self, label_or_field: str | Field) -> list:
        """Get a list of values of a field in the Barn."""
        if isinstance(label_or_field, Field):
            label_or_field = label_or_field.label
        return [getattr(seed, label_or_field) for seed in self]

    def __len__(self) -> int:
        """Return the number of seeds in the Barn.

        Returns:
            int: The number of seeds in the Barn.
        """
        return len(self._keyring_seed_map)

    def __repr__(self) -> str:
        length = len(self)
        word = "seed" if length == 1 else "seeds"
        return f"{self.__class__.__name__}({length} {word})"

    def __contains__(self, seed: Seed) -> bool:
        """Check if a seed is in the Barn.

        Args:
            seed: Seed to check for membership

        Returns:
            bool: True if the seed is in the Barn, False otherwise
        """
        return seed in self._keyring_seed_map.values()

    def __getitem__(self, index: int | slice):
        """Get a seed or a slice of seeds from the Barn.

        Args:
            index: int or slice of the seed(s) to retrieve

        Returns:
            Seed or Results: The retrieved seed(s)

        Raises:
            IndexError: If the index is not valid
        """
        seed_or_seeds = list(self._keyring_seed_map.values())[index]
        if type(index) is slice:
            results = Results(self.seed_model)
            [results.append(seed) for seed in seed_or_seeds]
            return results
        elif type(index) is int:
            return seed_or_seeds
        raise IndexError("Invalid index")

    def __iter__(self) -> Iterator[Seed]:
        """Iterate over the seeds in the Barn.

        E.g.: `for seed in barn: print(seed)`

        Yields:
            Seed: Each seed in the Barn, in the order they were added.
        """
        for seed in self._keyring_seed_map.values():
            yield seed


class Results(Barn):
    pass


class Branches(Barn):
    pass
