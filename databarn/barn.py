from typing import Any, Iterator

from .seed import Seed, metas


class Barn:

    def __init__(self, seed_model: Seed = Seed):
        # issubclass also returns True if the subclass is the parent class
        if not issubclass(seed_model, Seed):
            raise TypeError(
                "Only a Seed-derived class is permitted as model.")
        self.seed_model = seed_model
        self._next_autoid = 1
        self.seed_model = seed_model
        self._next_autoid = 1
        self._meta = metas.get_or_make(self.seed_model)
        self._keyring_seed_map: dict = {}

    def _assign_auto(self, seed: Seed, id: int) -> None:
        for spec in seed.__dna__.meta.specs:
            if spec.field.auto and getattr(seed, spec.label) is None:
                seed.__dict__[spec.label] = id

    def _validate_keyring(self, keyring: Any | tuple, is_comp_key: bool) -> None:
        if is_comp_key:
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
        self._validate_keyring(seed.__dna__.keyring,
                               seed.__dna__.is_comp_key)
        self._keyring_seed_map[seed.__dna__.keyring] = seed

    def _get_keyring(self, *keys, **named_keys) -> tuple[Any] | Any:
        if not keys and not named_keys:
            raise KeyError("No keys or named_keys were provided.")
        if keys and named_keys:
            raise KeyError("Both positional keys and named_keys "
                           "cannot be provided together.")
        keyring_len = len(self._meta.key_labels)
        if keys:
            if keyring_len != len(keys):
                raise KeyError(f"Expected {keyring_len} keys, "
                               f"got {len(keys)} instead.")
            keyring = keys[0] if len(keys) == 1 else keys
        else:
            if self._meta.is_dynamic:
                raise KeyError(
                    "To use named_keys, the provided seed_model for "
                    f"{self.__name__} cannot be dynamic.")
            if keyring_len != len(named_keys):
                raise KeyError(f"Expected {keyring_len} named_keys, "
                               f"got {len(named_keys)} instead.")
            key_lst = [named_keys[label] for label in self._meta.key_labels]
            keyring = tuple(key_lst)
        return keyring

    def get(self, *keys, **named_keys) -> Seed | None:
        keyring = self._get_keyring(*keys, **named_keys)
        return self._keyring_seed_map.get(keyring, None)

    def remove(self, seed: Seed) -> None:
        del self._keyring_seed_map[seed.__dna__.keyring]
        seed.__dna__.barns.discard(self)

    def _matches_criteria(self, seed: Seed, **named_fields) -> bool:
        for label, value in named_fields.items():
            if not hasattr(seed, label) or getattr(seed, label) != value:
                return False
        return True

    def find_all(self, **named_fields) -> "ResultsBarn":
        results = ResultsBarn(self.seed_model)
        for seed in self._keyring_seed_map.values():
            if self._matches_criteria(seed, **named_fields):
                results.append(seed)
        return results

    def find(self, **named_fields) -> Seed:
        for seed in self._keyring_seed_map.values():
            if self._matches_criteria(seed, **named_fields):
                return seed
        return None

    def _update_key(self, seed: Seed, key_name, new_key: Any) -> None:
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
        self._validate_keyring(new_keyring, seed.__dna__.meta.is_comp_key)
        old_keyring_seed_map = self._keyring_seed_map
        self._keyring_seed_map = {}
        for keyring, seed in old_keyring_seed_map.items():
            if keyring == seed.__dna__.keyring:
                keyring = new_keyring
            self._keyring_seed_map[keyring] = seed

    def __len__(self) -> int:
        return len(self._keyring_seed_map)

    def __repr__(self) -> str:
        length = len(self)
        word = "seed" if length == 1 else "seeds"
        return f"{self.__class__.__name__}({length} {word})"

    def __contains__(self, seed: Seed) -> bool:
        return seed in self._keyring_seed_map.values()

    def __getitem__(self, index) -> Seed:
        return list(self._keyring_seed_map.values())[index]

    def __iter__(self) -> Iterator[Seed]:
        for seed in self._keyring_seed_map.values():
            yield seed


class ResultsBarn(Barn):
    pass
