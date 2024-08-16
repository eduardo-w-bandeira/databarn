from typing import Any, Type, Tuple, Dict


class Cell:
    """Represents an attribute in a Seed model."""

    def __init__(self, type: Type | Tuple[Type] = type,
                 default: Any = None, key: bool = False,
                 auto: bool = False, none: bool = True,
                 frozen: bool = False):
        """
        Args:
            type: The type or tuple of types of the cell's value. Defaults to type.
            default: The default value of the cell. Defaults to None.
            key: Indicates whether this cell is the key. Defaults to False.
            auto: If True, Barn will auto-assign an incremental integer number. Defaults to False.
            none: Whether to allow the cell's value to be None. Defaults to True.
            frozen: If True, the cell's value cannot be modified after it has been assigned. Defaults to False.
        """
        self.type = type
        self.default = default
        # `is_key` differentiates it from `key`, which means 'key value' throughout the code.
        self.is_key = key
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
        for name, value in parent.__class__.__dict__.items():
            if isinstance(value, Cell):
                self.name_cell_map[name] = value
                self._unassigned_names.add(name)
        self.autoid = None
        # If the key is not provided, autoid will be used as key
        self._key_name = None
        self.barns = set()

    @property
    def key(self) -> Any:
        if self._key_name is None:
            return self.autoid
        return getattr(self._parent, self._key_name)

    def to_dict(self) -> Dict[str, Any]:
        map = {}
        for name in self.name_cell_map.keys():
            map[name] = getattr(self._parent, name)
        return map


class Seed:

    def __init__(self, *args, **kwargs):
        """
        Args:
            *args: Positional args to assign cell values in order of their definition.
            **kwargs: Keyword args to assign cell values by name.
        """
        self.__dict__.update(dna=Dna(self))  # => self.dna = Dna(self)
        for name, cell in self.dna.name_cell_map.items():
            if cell.is_key:
                if self.dna._key_name != None:
                    raise ValueError(
                        "Only one cell can be defined as key.")
                self.dna._key_name = name

        for index, value in enumerate(args):
            name = list(self.dna.name_cell_map.keys())[index]
            setattr(self, name, value)

        for name, value in kwargs.items():
            if name not in self.dna.name_cell_map:
                self.dna.name_cell_map[name] = Cell()
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
                msg = (f"The value of attribute `{name}` cannot be modified, "
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
            if cell.is_key and self.dna.barns:
                for barn in self.dna.barns:
                    barn._update_key(getattr(self, name), value)
            self.dna._unassigned_names.discard(name)
        super().__setattr__(name, value)

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.dna.to_dict().items()]
        return "{}({})".format(type(self).__name__, ", ".join(items))
