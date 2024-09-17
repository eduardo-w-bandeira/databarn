from typing import Any

type_ = type


class Field:
    label: str  # This is the key. It will be set later
    type: type_
    default: Any
    is_key: bool
    auto: bool
    frozen: bool
    none: bool
    assigned: bool  # It will be set later.

    def __init__(self, type: type_ | tuple[type_] = object,
                 default: Any = None, key: bool = False,
                 auto: bool = False, none: bool = True,
                 frozen: bool = False):
        if auto and type not in (int, object):
            raise TypeError(
                f"Only int or object are permitted as the type argument, and not {type}.")
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

    def copy(self) -> "Field":
        return Field(self.type, self.default, self.is_key,
                     self.auto, self.none, self.frozen)


class Meta:
    # seed_model: "Seed"
    fields: dict
    key_labels: list
    is_comp_key: bool
    key_defined: bool
    keyring_len: int
    dynamic: bool

    def __init__(self, seed_model: "Seed", new_fields: bool = False) -> None:
        # self.seed_model = seed_model
        self.key_labels = []
        self.fields = {}
        for label, field in seed_model.__dict__.items():
            if isinstance(field, Field):
                if new_fields:
                    field = field.copy()
                field.label = label
                self.fields[label] = field
                if field.is_key:
                    self.key_labels.append(label)
        self.dynamic = False if self.fields else True
        self.key_defined = len(self.key_labels) > 0
        self.is_comp_key = len(self.key_labels) > 1
        self.keyring_len = len(self.key_labels) or 1
