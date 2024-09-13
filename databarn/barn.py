from typing import Any, Iterator

from .cob import Cob, Field, infos


class Barn:

    def __init__(self, cob_model: Cob = Cob):
        # issubclass also returns True if the subclass is the parent class
        if not issubclass(cob_model, Cob):
            raise TypeError(
                "Only a Cob-derived class is permitted as model.")
        self.cob_model = cob_model
        self._next_autoid = 1
        self._keyring_cob_map = {}
        key_names = []
        for name, value in cob_model.__dict__.items():
            if isinstance(value, Field) and value.key:
                key_names.append(name)
        self._key_names = tuple(key_names)

    def _assign_auto(self, cob: Cob, id: int) -> None:
        for name, field in cob.__dna__.name_field_map.items():
            if field.auto and getattr(cob, name) is None:
                cob.__dict__[name] = id

    def _validate_keyring(self, keyring: Any | tuple, is_composite_key: bool) -> None:
        if is_composite_key:
            has_none = any(key is None for key in keyring)
            if has_none:
                raise KeyError("None is not valid as key.")
        elif keyring is None:
            raise KeyError("None is not valid as key.")
        if keyring in self._keyring_cob_map:
            raise KeyError(
                f"Key {keyring} already in use.")
        return True

    def append(self, cob: Cob) -> None:
        if self.cob_model is not Cob and type(cob) is not self.cob_model:
            raise TypeError(
                (f"Expected model {self.cob_model}, got {type(cob)}. "
                 "The provided cob is of a different type than the "
                 "model defined for this Barn."))
        if cob.__dna__.autoid is None:
            cob.__dna__.autoid = self._next_autoid
        self._assign_auto(cob, self._next_autoid)
        self._next_autoid += 1
        cob.__dna__.barns.add(self)
        self._validate_keyring(cob.__dna__.keyring,
                               cob.__dna__.is_composite_key)
        self._keyring_cob_map[cob.__dna__.keyring] = cob

    def get(self, *keys, **named_keys) -> Cob | None:
        if not keys and not named_keys:
            raise KeyError("No keys or named_keys were provided.")
        if key_lst and named_keys:
            raise KeyError("Both positional keys and named_keys "
                           "cannot be provided together.")

        keyring_len = len(self._key_names)
        if keys:
            if self.cob_model is not Cob:
                keys_len = len(keys)
                if keyring_len != keys_len:
                    raise KeyError(f"Expected {keyring_len} keys, "
                                   f"got {keys_len} instead.")
            keyring = keys[0] if len(keys) == 1 else keys
        elif named_keys:
            if self.cob_model is Cob:
                raise KeyError(
                    "To use named_keys, your seed model cannot be dynamic.")
            named_keys_len = len(named_keys)
            if keyring_len != named_keys_len:
                raise KeyError(f"Expected {keyring_len} named_keys, "
                               f"got {named_keys_len} instead.")
            keyring = tuple(named_keys[name] for name in self._key_names)
        return self._keyring_cob_map.get(keyring, None)

    def remove(self, cob: Cob) -> None:
        del self._keyring_cob_map[cob.__dna__.keyring]
        cob.__dna__.barns.discard(self)

    def _matches_criteria(self, cob: Cob, **kwargs) -> bool:
        for field_name, field_value in kwargs.items():
            if not hasattr(cob, field_name) or getattr(cob, field_name) != field_value:
                return False
        return True

    def find_all(self, **kwargs) -> "ResultsBarn":
        results = ResultsBarn(self.cob_model)
        for cob in self._keyring_cob_map.values():
            if self._matches_criteria(cob, **kwargs):
                results.append(cob)
        return results

    def find(self, **kwargs) -> Cob:
        for cob in self._keyring_cob_map.values():
            if self._matches_criteria(cob, **kwargs):
                return cob
        return None

    def _update_key(self, cob: Cob, key_name, new_key: Any) -> None:
        old_key = getattr(cob, key_name)
        if old_key == new_key:  # Prevent unecessary processing
            return
        new_keyring = new_key
        if cob.__dna__.is_composite_key:
            keys = []
            for name in cob.__dna__._key_names:
                key = getattr(cob, name)
                if name == key_name:
                    key = new_key
                keys.append(key)
            new_keyring = tuple(keys)
        self._validate_keyring(new_keyring, cob.__dna__.is_composite_key)
        old_keyring_cob_map = self._keyring_cob_map
        self._keyring_cob_map = {}
        for keyring, cob in old_keyring_cob_map.items():
            if keyring == cob.__dna__.keyring:
                keyring = new_keyring
            self._keyring_cob_map[keyring] = cob

    def __len__(self) -> int:
        return len(self._keyring_cob_map)

    def __repr__(self) -> str:
        length = len(self)
        word = "cob" if length == 1 else "cobs"
        return f"{self.__class__.__name__}({length} {word})"

    def __contains__(self, cob: Cob) -> bool:
        if cob in self._keyring_cob_map.values():
            return True
        return False

    def __getitem__(self, index) -> Cob:
        key = list(self._keyring_cob_map.keys())[index]
        return self._keyring_cob_map[key]

    def __iter__(self) -> Iterator[Cob]:
        for cob in self._keyring_cob_map.values():
            yield cob


class ResultsBarn(Barn):
    pass
