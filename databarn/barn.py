from typing import Any, Iterator

from .seed import Seed, Cell, infos


class Barn:

    def __init__(self, seed_model: Seed = Seed):
        # issubclass also returns True if the subclass is the parent class
        if not issubclass(seed_model, Seed):
            raise TypeError(
                "Only a Seed-derived class is permitted as seed_model.")
        self.seed_model = seed_model
        self._next_autoid = 1
        self._info = infos.get_or_make(self.seed_model)

    def _assign_auto(self, seed: Seed, id: int) -> None:
        for spec in seed.__dna__.info.specs:
            if spec.cell.auto and getattr(seed, spec.label) is None:
                seed.__dict__[spec.label] = id

    def _validate_keyring(self, keyring: Any | tuple, is_composite_key: bool) -> None:
        if is_composite_key:
            has_none = any(key is None for key in keyring)
            if has_none:
                raise KeyError("None is not valid as key.")
        elif keyring is None:
            raise KeyError("None is not valid as key.")
        if keyring in self._keyring_seed_map:
            raise KeyError(
                f"Key {keyring} already in use.")

    def append(self, seed: Seed) -> None:
        if not isinstance(seed, self.seed_model):
            raise TypeError(
                (f"Expected seed {self.seed_model}, got {type(seed)}. "
                 "The provided seed is not an instance of the seed_model "
                 "definied for this Barn."))
        if seed.__dna__.autoid is None:
            seed.__dna__.autoid = self._next_autoid
        self._assign_auto(seed, self._next_autoid)
        self._next_autoid += 1
        seed.__dna__.barns.add(self)
        self._validate_keyring(seed.__dna__.keyring,
                               seed.__dna__.info.is_composite_key)
        self._keyring_seed_map[seed.__dna__.keyring] = seed

    def get(self, *keys, **named_keys) -> Seed | None:
        if not keys and not named_keys:
            raise KeyError("No keys or named_keys were provided.")
        if keys and named_keys:
            raise KeyError("Both positional keys and named_keys "
                           "cannot be provided together.")

        keyring_len = len(self._key_names)
        if keys:
            if self.seed_model is not Seed:
                keys_len = len(keys)
                if keyring_len != keys_len:
                    raise KeyError(f"Expected {keyring_len} keys, "
                                   f"got {keys_len} instead.")
            keyring = keys[0] if len(keys) == 1 else keys
        elif named_keys:
            if self.seed_model is Seed:
                raise KeyError(
                    "To use named_keys, your model should static definied, not dynamic.")
            named_keys_len = len(named_keys)
            if keyring_len != named_keys_len:
                raise KeyError(f"Expected {keyring_len} named_keys, "
                               f"got {named_keys_len} instead.")
            keyring = tuple(named_keys[name] for name in self._key_names)
        return self._keyring_seed_map.get(keyring, None)

    def remove(self, seed: Seed) -> None:
        del self._keyring_seed_map[seed.__dna__.keyring]
        seed.__dna__.barns.discard(self)

    def _matches_criteria(self, seed: Seed, **kwargs) -> bool:
        for field_name, field_value in kwargs.items():
            if not hasattr(seed, field_name) or getattr(seed, field_name) != field_value:
                return False
        return True

    def find_all(self, **kwargs) -> "ResultsBarn":
        results = ResultsBarn(self.seed_model)
        for seed in self._keyring_seed_map.values():
            if self._matches_criteria(seed, **kwargs):
                results.append(seed)
        return results

    def find(self, **kwargs) -> Seed:
        for seed in self._keyring_seed_map.values():
            if self._matches_criteria(seed, **kwargs):
                return seed
        return None

    def _update_key(self, seed: Seed, key_name, new_key: Any) -> None:
        old_key = getattr(seed, key_name)
        if old_key == new_key:  # Prevent unecessary processing
            return
        new_keyring = new_key
        if seed.__dna__.is_composite_key:
            keys = []
            for name in seed.__dna__._key_names:
                key = getattr(seed, name)
                if name == key_name:
                    key = new_key
                keys.append(key)
            new_keyring = tuple(keys)
        self._validate_keyring(new_keyring, seed.__dna__.is_composite_key)
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
        if seed in self._keyring_seed_map.values():
            return True
        return False

    def __getitem__(self, index) -> Seed:
        key = list(self._keyring_seed_map.keys())[index]
        return self._keyring_seed_map[key]

    def __iter__(self) -> Iterator[Seed]:
        for seed in self._keyring_seed_map.values():
            yield seed


class ResultsBarn(Barn):
    pass
