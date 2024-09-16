from typing import Iterator, Any


class _Field:
    """Simplified version of Field, for internal use."""

    def __init__(self, key: bool = False):
        self.is_key = key

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        return "{}({})".format(type(self).__name__, ", ".join(items))


class _Seed:
    """Simplified version of Seed, for internal use."""

    def __init__(self, **kwargs) -> None:
        self.__dict__.update(**kwargs)


class _Barn:
    """Simplified version of Barn, for internal use."""

    def __init__(self) -> None:
        self._keyring_seed_map = {}

    def append(self, seed: _Seed) -> None:
        for label, value in seed.__class__.__dict__.items():
            if not isinstance(value, _Field):
                continue
            if value.is_key:
                key = getattr(seed, label)
                break
        if key in self._keyring_seed_map:
            raise Exception(f"Key {label}={key} already in use.")
        self._keyring_seed_map[key] = seed

    def get(self, key: Any) -> object | None:
        return self._keyring_seed_map.get(key, None)

    def has_key(self, key: Any):
        return key in self._keyring_seed_map

    def field_values(self, label: str) -> list:
        return [getattr(seed, label) for seed in self]

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

    def __contains__(self, seed: _Seed) -> bool:
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
            Seed or ResultsBarn: The retrieved seed(s)

        Raises:
            IndexError: If the index is not valid
        """
        seed_or_seeds = self._keyring_seed_map.values()[index]
        if type(index) is slice:
            results = _ResultsBarn(self.seed_model)
            for seed in seed_or_seeds:
                results.append(seed)
            return results
        if type(index) is int:
            return seed_or_seeds
        raise IndexError("Invalid index")

    def __iter__(self) -> Iterator[_Seed]:
        """Iterate over the seeds in the Barn.

        E.g.: `for seed in barn: print(seed)`

        Yields:
            Seed: Each seed in the Barn, in the order they were added.
        """
        for seed in self._keyring_seed_map.values():
            yield seed


class _ResultsBarn(_Barn):
    pass


class _Branches(_Barn):
    pass
