from typing import Any, Iterator

from .seed import Seed, Cell


class Barn:

    def __init__(self, model: Seed = Seed):
        # issubclass returns True when the subclass is the parent class
        if not issubclass(model, Seed):
            raise TypeError(
                "Only a Seed-derived class is permitted as model.")
        self.model = model
        self._next_autoid = 1
        self._keyring_seed_map = {}
        self._key_names = []
        for name, value in model.__dict__.items():
            if isinstance(value, Cell) and value.key:
                self._key_names.append(name)

    def _assign_auto(self, seed: Seed, id: int) -> None:
        for name, cell in seed.dna.name_cell_map.items():
            if cell.auto and getattr(seed, name) is None:
                seed.__dict__[name] = id

    def _validate_keyring(self, keyring: Any | tuple, is_composite_key: bool) -> None:
        if is_composite_key:
            has_none = any(key is None for key in keyring)
            if has_none:
                raise ValueError("None is not valid as key.")
        elif keyring is None:
            raise ValueError("None is not valid as key.")
        if keyring in self._keyring_seed_map:
            raise ValueError(
                f"Key {keyring} already in use.")

    def append(self, seed: Seed) -> None:
        """Adds a seed to the Barn. Barn keeps insertion order.

        Args:
            seed (Seed): The seed to be added.

        Raises:
            ValueError: If the key is already in use or is None.
        """
        if not isinstance(seed, self.model):
            raise TypeError(
                ("The provided seed is not an instance of the "
                 "model defined for this Barn."
                 f"Expected {self.model}, got {type(seed)}."))
        if seed.dna.autoid is None:
            seed.dna.autoid = self._next_autoid
        self._assign_auto(seed, self._next_autoid)
        self._next_autoid += 1
        seed.dna.barns.add(self)
        self._validate_keyring(seed.dna.keyring, seed.dna.is_composite_key)
        self._keyring_seed_map[seed.dna.keyring] = seed

    def get(self, *key_args, **key_kwargs) -> Seed | None:
        if key_args and key_kwargs:
            raise ValueError("Both positional and keyword arguments "
                             "should not be provided together.")
        if not key_args and not key_kwargs:
            raise ValueError("No key was provided.")
        if key_args:
            keyring = key_args[0] if len(key_args) == 1 else key_args
        elif self.model is Seed:
            raise KeyError("To use keyword arguments, you must provide "
                           "your model for Barn(SeedDerivedClass).")
        else:
            keyring = tuple(key_kwargs[name] for name in self._key_names)
        return self._keyring_seed_map.get(keyring, None)

    def remove(self, seed: Seed) -> None:
        """Removes a seed from the Barn.

        Args:
            seed (Seed): The seed to be removed.
        """
        del self._keyring_seed_map[seed.dna.keyring]
        seed.dna.barns.discard(self)

    def _matches_criteria(self, seed: Seed, **kwargs) -> bool:
        """Checks if a seed matches the given criteria.

        Args:
            seed: The object to check.
            **kwargs: Keyword arguments representing cell-value pairs to match.

        Returns:
            bool: True if the seed matches all criteria, False otherwise.
        """
        for cell_name, cell_value in kwargs.items():
            if not hasattr(seed, cell_name) or getattr(seed, cell_name) != cell_value:
                return False
        return True

    def find_all(self, **kwargs) -> "ResultsBarn":
        """Filter all seeds matching the given criteria.

        Args:
            **kwargs: Keyword arguments representing cell-value pairs to match.

        Returns:
            ResultBarn: A Barn of seeds that match the given criteria.
        """
        results = ResultsBarn(self.model)
        for seed in self._keyring_seed_map.values():
            if self._matches_criteria(seed, **kwargs):
                results.append(seed)
        return results

    def find(self, **kwargs) -> Seed:
        """Finds the first seed matching the given criteria.

        Args:
            **kwargs: Keyword arguments representing cell-value pairs to match.

        Returns:
            seed (Seed): The first seed that matches the given criteria, or None if no match is found.
        """
        for seed in self._keyring_seed_map.values():
            if self._matches_criteria(seed, **kwargs):
                return seed
        return None

    def _update_key(self, seed: Seed, key_name, new_key: Any) -> None:
        old_key = getattr(seed, key_name)
        if old_key == new_key:  # Prevent unecessary processing
            return
        new_keyring = new_key
        if seed.dna.is_composite_key:
            keys = []
            for name in seed.dna._key_names:
                key = getattr(seed, name)
                if name == key_name:
                    key = new_key
                keys.append(key)
            new_keyring = tuple(keys)
        self._validate_keyring(new_keyring, seed.dna.is_composite_key)
        old_keyring_seed_map = self._keyring_seed_map
        self._keyring_seed_map = {}
        for keyring, seed in old_keyring_seed_map.items():
            if keyring == seed.dna.keyring:
                keyring = new_keyring
            self._keyring_seed_map[keyring] = seed

    def __len__(self) -> int:
        return len(self._keyring_seed_map)

    def __repr__(self) -> str:
        count = len(self)
        word = "seed" if count == 1 else "seeds"
        return f"{self.__class__.__name__}({count} {word})"

    def __contains__(self, seed: Seed) -> bool:
        if seed in self._keyring_seed_map.values():
            return True
        return False

    def __getitem__(self, index) -> Seed:
        key = list(self._keyring_seed_map.keys())[index]
        return self._keyring_seed_map[key]

    def __iter__(self) -> Iterator[Seed]:
        """Iterates over the seeds in the Barn.

        Yields:
            Seed: Each seed in the Barn in insertion order.
        """
        for seed in self._keyring_seed_map.values():
            yield seed


class ResultsBarn(Barn):
    pass
