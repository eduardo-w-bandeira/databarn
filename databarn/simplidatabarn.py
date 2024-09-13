from typing import Iterator, Any


class _Field:
    """Simplified version of Cob, for internal use."""

    def __init__(self, key: bool = False):
        self.type = type
        self.key = key

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        return "{}({})".format(type(self).__name__, ", ".join(items))


class _Cob:
    """Simplified version of Cob, for internal use."""

    def __init__(self, **kwargs) -> None:
        self.__dict__.update(**kwargs)


class _Barn:
    """Simplified version of Barn, for internal use."""

    def __init__(self) -> None:
        self._key_cob_map = {}

    def append(self, cob: _Cob) -> None:
        for label, value in cob.__class__.__dict__.items():
            if not isinstance(value, _Field):
                continue
            if value.key:
                key = getattr(cob, label)
                break
        if key in self._key_cob_map:
            raise Exception(f"Key {label}={key} already in use.")
        self._key_cob_map[key] = cob

    def get(self, key: Any) -> object | None:
        return self._key_cob_map.get(key, None)

    def has_key(self, key: Any):
        return key in self._key_cob_map

    def field_values(self, label: str) -> tuple:
        return tuple(getattr(cob, label) for cob in self)

    def __len__(self) -> int:
        return len(self._key_cob_map)

    def __repr__(self) -> str:
        length = len(self)
        word = "cob" if length == 1 else "cobs"
        return f"{self.__class__.__name__}({length} {word})"

    def __contains__(self, cob: object) -> bool:
        if cob in self._key_cob_map.values():
            return True
        return False

    def __getitem__(self, index: int) -> object:
        key = list(self._key_cob_map.keys())[index]
        return self._key_cob_map[key]

    def __iter__(self) -> Iterator[object]:
        for cob in self._key_cob_map.values():
            yield cob


class _Branches(_Barn):
    pass
