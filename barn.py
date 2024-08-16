from typing import Any, Iterator

from databarn.seed import Seed


class Barn:

    def __init__(self):
        self._next_autoid = 1
        self._key_seed_map = {}

    def _assign_auto(self, seed: Seed, id: int) -> None:
        for name, cell in seed.dna.name_cell_map.items():
            if cell.auto and getattr(seed, name) is None:
                seed.__dict__[name] = id

    def _check_key_validity(self, key: Any) -> None:
        if key is None:
            raise ValueError("None is not valid as key.")
        elif key in self._key_seed_map:
            raise ValueError(
                f"Key {key} already in use.")

    def append(self, seed: Seed) -> None:
        """Adds a seed to the Barn. Barn keeps insertion order.

        Args:
            seed (Seed): The seed to be added.

        Raises:
            ValueError: If the key is already in use or is None.
        """
        if seed.dna.autoid is None:
            seed.dna.autoid = self._next_autoid
        self._assign_auto(seed, self._next_autoid)
        self._next_autoid += 1
        self._check_key_validity(seed.dna.key)
        seed.dna.barns.add(self)
        self._key_seed_map[seed.dna.key] = seed

    def get(self, key: Any) -> Seed | None:
        """Retrieves a seed by its key.

        Args:
            key (Any): The key of the seed.

        Returns:
            seed (Seed): The seed, or None if not found.
        """
        return self._key_seed_map.get(key, None)

    def remove(self, seed: Seed) -> None:
        """Removes a seed from the Barn.

        Args:
            seed (Seed): The seed to be removed.
        """
        del self._key_seed_map[seed.dna.key]
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
            if getattr(seed, cell_name) != cell_value:
                return False
        return True

    def find_all(self, **kwargs) -> "ResultsBarn":
        """Finds all seeds matching the given criteria.

        Args:
            **kwargs: Keyword arguments representing cell-value pairs to match.

        Returns:
            ResultBarn: A Barn of seeds that match the given criteria.
        """
        results = ResultsBarn()
        for seed in self._key_seed_map.values():
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
        for seed in self._key_seed_map.values():
            if self._matches_criteria(seed, **kwargs):
                return seed
        return None

    def _update_key(self, old: Any, new: Any) -> None:
        if old == new:
            return
        self._check_key_validity(new)
        old_key_seed_map = self._key_seed_map
        self._key_seed_map = {}
        for key, seed in old_key_seed_map.items():
            if key == old:
                key = new
            self._key_seed_map[key] = seed

    def __len__(self) -> int:
        return len(self._key_seed_map)

    def __repr__(self) -> str:
        count = len(self)
        word = "seed" if count == 1 else "seeds"
        return f"{self.__class__.__name__}({count} {word})"

    def __contains__(self, seed: Seed) -> bool:
        if seed in self._key_seed_map.values():
            return True
        return False

    def __getitem__(self, index) -> Seed:
        key = list(self._key_seed_map.keys())[index]
        return self._key_seed_map[key]

    def __iter__(self) -> Iterator[Seed]:
        """Iterates over the seeds in the Barn.

        Yields:
            Seed: Each seed in the Barn in insertion order.
        """
        for seed in self._key_seed_map.values():
            yield seed


class ResultsBarn(Barn):
    pass
