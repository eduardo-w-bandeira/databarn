from typing import Any
from databarn.simplidatabarn import _Cell, _Cell, _Barn, _Branches

# Glossary
# label = attribute name


class Cell:

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


class Spec(_Cell):
    label: str = _Cell(key=True)
    cell: Cell = _Cell()


class Info(_Cell):
    seed_model: "Seed" = _Cell(key=True)
    specs: _Branches = _Cell()
    key_labels: tuple = _Cell()
    is_composite_key: bool = _Cell()
    is_dynamic: bool = _Cell()


def extract_info(seed_model: "Seed"):
    key_labels = []
    specs = _Branches()
    for label, value in seed_model.__dict__.items():
        if isinstance(value, _Cell):
            spec = Spec(label=label,
                        cell=value,
                        assigned=False)
            specs.append(spec)
        if value.key:
            key_labels.append(label)
    is_composite_key = True if len(key_labels) > 1 else False
    is_dynamic = False if specs else True
    info = Info(seed_model=seed_model,
                specs=specs,
                key_labels=tuple(key_labels),
                is_composite_key=is_composite_key,
                is_dynamic=is_dynamic)
    return info


class Infos(_Barn):

    def get_or_make(self, seed_model: "Seed") -> Info:
        if not self.has_key(seed_model):
            info = Info.make_info(seed_model)
            self.append(info)
        return self.get(seed_model)


infos = Infos()


class Dna():

    def __init__(self, seed: "Seed"):
        self._seed = seed
        self.info = infos.get_or_make(seed.__class__)
        if self.info.is_dynamic:
            # Create a new object, so specs can be appended
            self.info = extract_info(seed.__class__)
        self._unassigned_labels = set(spec.label for spec in self.info.specs)
        self.autoid: int | None = None
        # If the key is not provided, autoid will be used as key
        self.barns = set()

    def _add_dynamic_spec(self, label, cell):
        assert self.info.is_dynamic is True
        spec = Spec(label=label, cell=cell)
        self.info.specs.append(spec)
        self._unassigned_labels.add(spec.label)

    @property
    def keyring(self) -> Any | tuple[Any]:
        if not self.info.key_labels:
            return self.autoid
        keys = [getattr(self._seed, label) for label in self.info.key_labels]
        if len(keys) == 1:
            return keys[0]
        return tuple(keys)

    def to_dict(self) -> dict[str, Any]:
        labels = self.info.specs.field_values("label")
        return {label: getattr(self._seed, label) for label in labels}


class Seed:

    def __init__(self, *args, **kwargs):
        self.__dict__.update(__dna__=Dna(self))  # => self.__dna__ = Dna(self)

        labels = self.__dna__.info.specs.get_values("label")

        for index, value in enumerate(args):
            label = labels[index]
            setattr(self, label, value)

        for label, value in kwargs.items():
            if self.__dna__.info.is_dynamic:
                self.__dna__._add_dynamic_spec(label, Cell())
            elif label not in labels:
                raise ValueError(f"Cell '{label}' was not defined in your Seed. "
                                 "If you define any static cell in the Seed, "
                                 "you cannot use dynamic cell creation.")
            setattr(self, label, value)

        for label in list(self.__dna__._unassigned_labels):
            spec = self.__dna__.info.specs.get(label)
            setattr(self, label, spec.cell.default)

    def __setattr__(self, name: str, value: Any):
        if (spec := self.__dna__.info.specs.get(name)):
            cell = spec.cell
            was_assigned = False if name in self.__dna__._unassigned_labels else True
            if cell.frozen and was_assigned:
                msg = (f"Cannot assign `{value}` to attribute `{name}`, "
                       "since it was defined as frozen.")
                raise AttributeError(msg)
            if not isinstance(value, cell.type) and value is not None:
                msg = (f"Type mismatch for attribute `{name}`. "
                       f"Expected {cell.type}, got {type(value).__name__}.")
                raise TypeError(msg)
            if cell.auto:
                if not was_assigned and value is None:
                    pass
                else:
                    msg = (f"Cannot assign `{value}` to attribute `{name}`, "
                           "since it was defined as auto.")
                    raise AttributeError(msg)
            elif not cell.none and value is None:
                msg = (f"Cannot assign `{value}` to attribute `{name}`, "
                       "since it was defined as none=False.")
                raise ValueError(msg)
            if cell.key and self.__dna__.barns:
                for barn in self.__dna__.barns:
                    barn._update_key(self, name, value)
            self.__dna__._unassigned_labels.discard(name)
        super().__setattr__(name, value)

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.__dna__.to_dict().items()]
        return "{}({})".format(type(self).__name__, ", ".join(items))
