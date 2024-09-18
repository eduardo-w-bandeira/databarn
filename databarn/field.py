from typing import Any, Type

type_ = type


class Field:
    # Seed model
    label: str  # key for seed.__dna__.label_field_map. It will be set later
    type: type_
    default: Any
    is_key: bool
    auto: bool
    frozen: bool
    none: bool
    # Seed instance
    seed: "Seed"  # It will be set later, only in the seed instances
    assigned: bool  # It will be set later, only in the seed instances
    value: Any  # Only for getting. It was used @property

    def __init__(self, type: type_ | tuple[type_] = object,
                 default: Any = None, key: bool = False,
                 auto: bool = False, none: bool = True,
                 frozen: bool = False, **kwargs):
        if auto and type not in (int, object):
            raise TypeError(
                f"Expected int or object for type arg, but got {type}.")
        self.type = type
        self.default = default
        # is_key to prevent conflict with "key" (used as value throughout the code)
        self.is_key = key
        self.auto = auto
        self.frozen = frozen
        self.none = none
        self.__dict__.update(kwargs)

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        return "{}({})".format(type(self).__name__, ", ".join(items))

    @property
    def value(self):
        return getattr(self.seed, self.label)
