from typing import Any, Iterator

from .seed import Seed, metas


class Barn:
    """In-memory storage for seed-like objects.

    Provides methods to find and retrieve
    Seed objects based on their keys or fields.
    """

    def __init__(self, seed_model: Seed = Seed):
        # issubclass also returns True if the subclass is the parent class
        """Initialize the Barn.

        Args:
            seed_model: The Seed-like class whose objects will be stored in this Barn.
        """
        if not issubclass(seed_model, Seed):
            raise TypeError(
                "Only a Seed-derived class is permitted as model.")
        self.seed_model = seed_model
        self._next_autoid = 1
        self._seed_meta = metas.get_or_make(self.seed_model)
        self._keyring_seed_map: dict = {}

    def _assign_auto(self, seed: Seed, id: int) -> None:
        """Assign an auto field value to the seed, if applicable.

        Args:
            seed: The seed whose auto fields should be assigned.
            id: The value to assign to the auto fields.
        """
        for field in seed.__dna__.meta.fields:
            if field.auto and getattr(seed, field.label) is None:
                seed.__dict__[field.label] = id

    def _validate_keyring(self, keyring: Any | tuple) -> bool:
        """Check if the key(s) is unique and not None.

        Args:
            keyring: The key or tuple of composite keys.

        Returns:
            True if the keyring is valid.

        Raises:
            KeyError: If the keyring is None or already in use.
        """
        if self._seed_meta.is_comp_key:
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
                (f"Expected seed {self.seed_model}, got {type(seed)}. "
                 "The provided seed is of a different type than the "
                 "model defined for this Barn."))
        if seed.__dna__.autoid is None:
            seed.__dna__.autoid = self._next_autoid
        self._assign_auto(seed, self._next_autoid)
        self._next_autoid += 1
        seed.__dna__.barns.add(self)
        self._validate_keyring(seed.__dna__.keyring)
        self._keyring_seed_map[seed.__dna__.keyring] = seed

    def _get_keyring(self, *keys, **named_keys) -> tuple[Any] | Any:
        """Return a keyring as a tuple of keys or a single key.

        You can provide either positional args or kwargs, but not both.

        Raises:
            SyntaxError: If nothing was provided, or
                both positional keys and named_keys were provided, or
                the number of keys does not match the key fields.
        """

        if not keys and not named_keys:
            raise SyntaxError("No keys or named_keys were provided.")
        if keys and named_keys:
            raise SyntaxError("Both positional keys and named_keys "
                              "cannot be provided together.")
        if keys:
            if self._seed_meta.keyring_len != len(keys):
                raise SyntaxError(f"Expected {self._seed_meta.keyring_len} keys, "
                                  f"got {len(keys)} instead.")
            keyring = keys[0] if len(keys) == 1 else keys
        else:
            if self._seed_meta.dynamic:
                raise SyntaxError(
                    "To use named_keys, the provided seed_model for "
                    f"{self.__name__} cannot be dynamic.")
            if self._seed_meta.keyring_len != len(named_keys):
                raise SyntaxError(f"Expected {self._seed_meta.keyring_len} named_keys, "
                                  f"got {len(named_keys)} instead.")
            key_lst = [named_keys[label]
                       for label in self._seed_meta.key_labels]
            keyring = tuple(key_lst)
        return keyring

    def get(self, *keys, **named_keys) -> Seed | None:
        """Return a seed from the Barn, given its key or named keys.

        Raises:
            SyntaxError: If nothing was provided, or
                both positional keys and named_keys were provided, or
                the number of keys does not match the key fields.

        Returns:
            Seed | None: The seed associated with the key(s), or None if not found.
        """
        keyring = self._get_keyring(*keys, **named_keys)
        return self._keyring_seed_map.get(keyring, None)

    def remove(self, seed: Seed) -> None:
        """Remove a seed from the Barn.

        Args:
            seed: The seed to remove
        """
        del self._keyring_seed_map[seed.__dna__.keyring]
        seed.__dna__.barns.discard(self)

    def _matches_criteria(self, seed: Seed, **named_fields) -> bool:
        """Check if a seed matches the given criteria.

        Args:
            seed: The seed to check
            **named_fields: The criteria to match

        Returns:
            bool: True if the seed matches the criteria, False otherwise
        """
        for label, value in named_fields.items():
            if not hasattr(seed, label) or getattr(seed, label) != value:
                return False
        return True

    def find_all(self, **named_fields) -> "ResultsBarn":
        """Find all seeds in the Barn that match the given criteria.

        Args:
            **named_fields: The criteria to match

        Returns:
            ResultsBarn: A ResultsBarn containing all seeds that match the criteria
        """
        results = ResultsBarn(self.seed_model)
        for seed in self._keyring_seed_map.values():
            if self._matches_criteria(seed, **named_fields):
                results.append(seed)
        return results

    def find(self, **named_fields) -> Seed:
        """Find the first seed in the Barn that matches the given criteria.

        Args:
            **named_fields: The criteria to match

        Returns:
            Seed: The first seed that matches the criteria, or None not found.
        """
        for seed in self._keyring_seed_map.values():
            if self._matches_criteria(seed, **named_fields):
                return seed
        return None

    def _update_key(self, seed: Seed, key_name: str, new_key: Any) -> None:
        """Update the keyring of a seed in the Barn.

        Args:
            seed: The seed whose keyring needs to be updated
            key_name: The name of the key to update
            new_key: The new key

        This method will update the keyring of the seed and
        reindex the seed in the Barn. If the key is not unique or
        is None, a KeyError is raised.
        """
        old_key = getattr(seed, key_name)
        if old_key == new_key:  # Prevent unecessary processing
            return
        new_keyring = new_key
        if seed.__dna__.meta.is_comp_key:
            keys = []
            for name in seed.__dna__.meta.key_labels:
                key = getattr(seed, name)
                if name == key_name:
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

    def __getitem__(self, index: int | slice) -> Seed | "ResultsBarn":
        """Get a seed or a slice of seeds from the Barn.

        Args:
            index: int or slice of the seed(s) to retrieve

        Returns:
            Seed or ResultsBarn: The retrieved seed(s)

        Raises:
            IndexError: If the index is not valid
        """
        seed_or_seeds = self._keyring_seed_map.values()[index]
        if type(index) is slice:
            results = ResultsBarn(self.seed_model)
            for seed in seed_or_seeds:
                results.append(seed)
            return results
        if type(index) is int:
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


class ResultsBarn(Barn):
    pass
