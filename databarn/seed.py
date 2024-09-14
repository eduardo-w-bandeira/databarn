from typing import Any
from .field import Field
from .simplidatabarn import _Field, _Seed, _Barn, _Branches

# Glossary
# label = attribute name


class Spec(_Seed):
    label: str = _Field(key=True)
    field: _Field = _Field()


class Meta(_Seed):
    seed_model: "Seed" = _Field(key=True)
    specs: _Branches = _Field()
    key_labels: list = _Field()
    keyring_len: int = _Field()
    is_comp_key: bool = _Field()
    dynamic: bool = _Field()


def extract_meta(seed_model: "Seed"):
    key_labels = []
    specs = _Branches()
    for label, value in seed_model.__dict__.items():
        if isinstance(value, Field):
            spec = Spec(label=label, field=value)
            specs.append(spec)
            if value.is_key:
                key_labels.append(label)
    is_comp_key = True if len(key_labels) > 1 else False
    dynamic = False if specs else True
    keyring_len = 1 if dynamic else len(key_labels)
    meta = Meta(seed_model=seed_model,
                specs=specs,
                key_labels=key_labels,
                is_comp_key=is_comp_key,
                dynamic=dynamic,
                keyring_len=keyring_len)
    return meta


class Metas(_Barn):

    def get_or_make(self, seed_model: "Seed") -> Meta:
        if not self.has_key(seed_model):
            meta = extract_meta(seed_model)
            self.append(meta)
        return self.get(seed_model)


metas = Metas()


class Dna():

    def __init__(self, seed: "Seed"):
        self._seed = seed
        self.meta = metas.get_or_make(seed.__class__)
        if self.meta.dynamic:
            # Create a new object, so specs can be appended
            self.meta = extract_meta(seed.__class__)
        self._unassigned_labels = set(spec.label for spec in self.meta.specs)
        self.autoid: int | None = None
        # If the key is not provided, autoid will be used as key
        self.barns = set()

    def _add_dynamic_spec(self, label, field):
        assert self.meta.dynamic is True
        spec = Spec(label=label, field=field)
        self.meta.specs.append(spec)
        self._unassigned_labels.add(spec.label)

    @property
    def keyring(self) -> Any | tuple[Any]:
        if not self.meta.key_labels:
            return self.autoid
        keys = [getattr(self._seed, label) for label in self.meta.key_labels]
        if len(keys) == 1:
            return keys[0]
        return tuple(keys)

    def to_dict(self) -> dict[str, Any]:
        labels = self.meta.specs.field_values("label")
        return {label: getattr(self._seed, label) for label in labels}


class Seed:

    def __init__(self, *args, **kwargs):
        self.__dict__.update(__dna__=Dna(self))  # => self.__dna__ = Dna(self)

        labels = self.__dna__.meta.specs.field_values("label")

        for index, value in enumerate(args):
            label = labels[index]
            setattr(self, label, value)

        for label, value in kwargs.items():
            if self.__dna__.meta.dynamic:
                self.__dna__._add_dynamic_spec(label, Field())
            elif label not in labels:
                raise ValueError(f"Field '{label}' was not defined in your Seed. "
                                 "If you define any static field in the Seed, "
                                 "you cannot use dynamic field creation.")
            setattr(self, label, value)

        for label in list(self.__dna__._unassigned_labels):
            spec = self.__dna__.meta.specs.get(label)
            setattr(self, label, spec.field.default)

    def __setattr__(self, name: str, value: Any):
        if (spec := self.__dna__.meta.specs.get(name)):
            field = spec.field
            was_assigned = False if name in self.__dna__._unassigned_labels else True
            if field.frozen and was_assigned:
                msg = (f"Cannot assign `{value}` to attribute `{name}`, "
                       "since it was defined as frozen.")
                raise AttributeError(msg)
            if not isinstance(value, field.type) and value is not None:
                msg = (f"Type mismatch for attribute `{name}`. "
                       f"Expected {field.type}, got {type(value).__name__}.")
                raise TypeError(msg)
            if field.auto:
                if not was_assigned and value is None:
                    pass
                else:
                    msg = (f"Cannot assign `{value}` to attribute `{name}`, "
                           "since it was defined as auto.")
                    raise AttributeError(msg)
            elif not field.none and value is None:
                msg = (f"Cannot assign `{value}` to attribute `{name}`, "
                       "since it was defined as none=False.")
                raise ValueError(msg)
            if field.is_key and self.__dna__.barns:
                for barn in self.__dna__.barns:
                    barn._update_key(self, name, value)
            self.__dna__._unassigned_labels.discard(name)
        super().__setattr__(name, value)

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.__dna__.to_dict().items()]
        return "{}({})".format(type(self).__name__, ", ".join(items))
