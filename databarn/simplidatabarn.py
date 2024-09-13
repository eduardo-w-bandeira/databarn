from typing import Iterator, Any


class _Cell:
    """Simplified version of Seed, for internal use."""

    def __init__(self, key: bool = False):
        self.type = type
        self.key = key

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        return "{}({})".format(type(self).__name__, ", ".join(items))


class _Cell:
    """Simplified version of Seed, for internal use."""

    def __init__(self, **kwargs) -> None:
        self.__dict__.update(**kwargs)


class _Barn:
    """Simplified version of Barn, for internal use."""

    def __init__(self) -> None:
        self._key_seed_map = {}

    def append(self, seed: _Cell) -> None:
        for label, value in seed.__class__.__dict__.items():
            if not isinstance(value, _Cell):
                continue
            if value.key:
                key = getattr(seed, label)
                break
        if key in self._key_seed_map:
            raise Exception(f"Key {label}={key} already in use.")
        self._key_seed_map[key] = seed

    def get(self, key: Any) -> object | None:
        return self._key_seed_map.get(key, None)

    def has_key(self, key: Any):
        return key in self._key_seed_map

    def field_values(self, label: str) -> tuple:
        return tuple(getattr(seed, label) for seed in self)

    def __len__(self) -> int:
        return len(self._key_seed_map)

    def __repr__(self) -> str:
        length = len(self)
        word = "seed" if length == 1 else "seeds"
        return f"{self.__class__.__name__}({length} {word})"

    def __contains__(self, seed: object) -> bool:
        if seed in self._key_seed_map.values():
            return True
        return False

    def __getitem__(self, index: int) -> object:
        key = list(self._key_seed_map.keys())[index]
        return self._key_seed_map[key]

    def __iter__(self) -> Iterator[object]:
        for seed in self._key_seed_map.values():
            yield seed


class _Branches(_Barn):
    pass
