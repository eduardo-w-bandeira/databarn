from typing import Any
from .simplidatabarn import _Field, _Seed

type_ = type


class Field(_Seed):
    label: str = _Field(key=True)
    type: type_ = _Field()
    default: Any = _Field()
    # is_key to prevent conflict with "key" (used as value throughout the code)
    is_key: bool = _Field()
    auto: bool = _Field()
    frozen: bool = _Field()
    none: bool = _Field()

    def __init__(self, type: type_ | tuple[type] = object,
                 default: Any = None, key: bool = False,
                 auto: bool = False, none: bool = True,
                 frozen: bool = False):
        if auto and type not in (int, object):
            raise TypeError(
                f"Only int or object are permitted as the type argument, and not {type}.")
        self.label = None
        self.type = type
        self.default = default
        # is_key to prevent conflict with "key" (used as value throughout the code)
        self.is_key = key
        self.auto = auto
        self.frozen = frozen
        self.none = none

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        return "{}({})".format(type(self).__name__, ", ".join(items))
