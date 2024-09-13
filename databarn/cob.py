from typing import Any
from databarn.simplidatabarn import _Field, _Cob, _Barn, _Branches

# Glossary
# label = attribute name


class Field:

    def __init__(self, type: type | tuple[type] = object,
                 default: Any = None, key: bool = False,
                 auto: bool = False, none: bool = True,
                 frozen: bool = False):
        if auto and type not in (int, object):
            raise TypeError(
                f"Only int or object are permitted as the type argument, and not {type}.")
        self.type = type
        self.default = default
        self.key = key
        self.auto = auto
        self.frozen = frozen
        self.none = none

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        return "{}({})".format(type(self).__name__, ", ".join(items))


class Spec(_Cob):
    label: str = _Field(key=True)
    field: Field = _Field()


class Info(_Cob):
    cob_model: "Cob" = _Field(key=True)
    specs: _Branches = _Field()
    key_labels: tuple = _Field()
    composite_key: bool = _Field()
    dynamic: bool = _Field()


def extract_info(cob_model: "Cob"):
    key_labels = []
    specs = _Branches()
    for label, value in cob_model.__dict__.items():
        if isinstance(value, _Field):
            spec = Spec(label=label,
                        field=value,
                        assigned=False)
            specs.append(spec)
        if value.key:
            key_labels.append(label)
    composite_key = True if len(key_labels) > 1 else False
    dynamic = False if specs else True
    info = Info(cob_model=cob_model,
                specs=specs,
                key_labels=tuple(key_labels),
                composite_key=composite_key,
                dynamic=dynamic)
    return info


class Infos(_Barn):

    def get_or_make(self, cob_model: "Cob") -> Info:
        if not self.has_key(cob_model):
            info = Info.make_info(cob_model)
            self.append(info)
        return self.get(cob_model)


infos = Infos()


class Dna():

    def __init__(self, cob: "Cob"):
        self._cob = cob
        self.info = infos.get_or_make(cob.__class__)
        if self.info.dynamic:
            # Create a new object, so specs can be appended
            self.info = extract_info(cob.__class__)
        self._unassigned_labels = set(spec.label for spec in self.info.specs)
        self.autoid: int | None = None
        # If the key is not provided, autoid will be used as key
        self.barns = set()

    def _add_dynamic_spec(self, label, field):
        assert self.info.dynamic is True
        spec = Spec(label=label, field=field)
        self.info.specs.append(spec)
        self._unassigned_labels.add(spec.label)

    @property
    def keyring(self) -> Any | tuple[Any]:
        if not self.info.key_labels:
            return self.autoid
        keys = [getattr(self._cob, label) for label in self.info.key_labels]
        if len(keys) == 1:
            return keys[0]
        return tuple(keys)

    def to_dict(self) -> dict[str, Any]:
        labels = self.info.specs.field_values("label")
        return {label: getattr(self._cob, label) for label in labels}


class Cob:

    def __init__(self, *args, **kwargs):
        self.__dict__.update(__dna__=Dna(self))  # => self.__dna__ = Dna(self)

        labels = self.__dna__.info.specs.get_values("label")

        for index, value in enumerate(args):
            label = labels[index]
            setattr(self, label, value)

        for label, value in kwargs.items():
            if self.__dna__.info.dynamic:
                self.__dna__._add_dynamic_spec(label, Field())
            elif label not in labels:
                raise ValueError(f"Field '{label}' was not defined in your Cob. "
                                 "If you define any static field in the Cob, "
                                 "you cannot use dynamic field creation.")
            setattr(self, label, value)

        for label in list(self.__dna__._unassigned_labels):
            spec = self.__dna__.info.specs.get(label)
            setattr(self, label, spec.field.default)

    def __setattr__(self, name: str, value: Any):
        if (spec := self.__dna__.info.specs.get(name)):
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
            if field.key and self.__dna__.barns:
                for barn in self.__dna__.barns:
                    barn._update_key(self, name, value)
            self.__dna__._unassigned_labels.discard(name)
        super().__setattr__(name, value)

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.__dna__.to_dict().items()]
        return "{}({})".format(type(self).__name__, ", ".join(items))
