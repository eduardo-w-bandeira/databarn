from typing import Any


class Cell:
    """Represents an attribute in a Seed model."""

    def __init__(self, type: type | tuple[type] = object,
                 default: Any = None, key: bool = False,
                 auto: bool = False, none: bool = True,
                 frozen: bool = False):
        """
        Args:
            type: The type or tuple of types of the cell's value. Defaults to object.
            default: The default value of the cell. Defaults to None.
            key: Indicates whether this cell is the key. Defaults to False.
            auto: If True, Barn will auto-assign an incremental integer number. Defaults to False.
            none: Whether to allow the cell's value to be None. Defaults to True.
            frozen: If True, the cell's value cannot be modified after it has been assigned. Defaults to False.
        """
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


class Dna:

    def __init__(self, parent: "Seed"):
        self._parent = parent
        self.name_cell_map = {}
        self._unassigned_names = set()
        self._key_names = []
        self.autoid: int | None = None
        # If the key is not provided, autoid will be used as key
        self.barns = set()
        for name, value in parent.__class__.__dict__.items():
            self._add_name_cell_if(name, value)
        self.is_composite_key = True if len(self._key_names) > 1 else False

    def _add_name_cell_if(self, name, value):
        if not isinstance(value, Cell):
            return
        self.name_cell_map[name] = value
        if value.key:
            self._key_names.append(name)
        self._unassigned_names.add(name)

    @property
    def keyring(self) -> Any | tuple[Any]:
        if not self._key_names:
            return self.autoid
        keys = [getattr(self._parent, name) for name in self._key_names]
        if len(keys) == 1:
            return keys[0]
        return tuple(keys)

    @property
    def key_value_map(self) -> dict[str, Any]:
        return {name: getattr(self._parent, name) for name in self._key_names}

    def to_dict(self) -> dict[str, Any]:
        names = self.name_cell_map.keys()
        return {name: getattr(self._parent, name) for name in names}


class Seed:

    def __init__(self, *args, **kwargs):
        """
        Args:
            *args: Positional args to assign cell values in order of their definition.
            **kwargs: Keyword args to assign cell values by name.
        """
        self.__dict__.update(dna=Dna(self))  # => self.dna = Dna(self)

        for index, value in enumerate(args):
            name = list(self.dna.name_cell_map.keys())[index]
            setattr(self, name, value)

        for name, value in kwargs.items():
            if name not in self.dna.name_cell_map:
                self.dna._add_name_cell_if(name, Cell())
            setattr(self, name, value)

        for name in list(self.dna._unassigned_names):
            cell = self.dna.name_cell_map[name]
            setattr(self, name, cell.default)

    def __setattr__(self, name: str, value: Any):
        """Sets an attribute value, enforcing type checks and checking for frozen attributes.

        Args:
            name: The name of the attribute.
            value: The value to be assigned to the attribute.

        Raises:
            AttributeError: If the cell is set to frozen and the value is changed after assignment.
            TypeError: If the value type does not match the expected type defined in the Field.
        """
        if name in self.dna.name_cell_map:
            cell = self.dna.name_cell_map[name]
            was_assigned = False if name in self.dna._unassigned_names else True
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
            if cell.key and self.dna.barns:
                for barn in self.dna.barns:
                    barn._update_key(self, name, value)
            self.dna._unassigned_names.discard(name)
        super().__setattr__(name, value)

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.dna.to_dict().items()]
        return "{}({})".format(type(self).__name__, ", ".join(items))
