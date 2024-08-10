"""
Simple in-memory ORM and data carrier
"""
from typing import Any, Type, List, Tuple

__all__ = ["Seed", "Cell", "Barn"]


class Cell:
    """Represents an attribute in a Seed model."""

    def __init__(self, type: Type | Tuple[Type] = object,
                 default: Any = None, is_key: bool = False,
                 auto: bool = False, frozen: bool = False):
        """
        Args:
            type (type or tuple): The type or tuple of types of the cell's value. Defaults to object.
            default (Any): The default value of the cell. Defaults to None.
            is_key (bool): Indicates whether this cell is the key. Defaults to False.
            auto (bool): If True, Barn will assign an incremental integer number to the cell. Defaults to False.
            frozen (bool): If True, the cell's value cannot be modified after it has been assigned. Defaults to False.
        """
        self.type = type
        self.default = default
        self.is_key = is_key
        self.auto = auto
        self.frozen = frozen


class Wiz:

    def __init__(self, parent):
        self._parent = parent
        self._name_cell_map = {}
        self.autoid = None
        # If the key is not provided, autoid will be used as key
        self._key_name = None
        self.barns = set()

    @property
    def _key(self) -> Any:
        if self._key_name is None:
            return self.autoid
        return getattr(self._parent, self._key_name)

    @property
    def name_value_map(self) -> dict:
        map = {}
        for name in self._name_cell_map.keys():
            map[name] = getattr(self._parent, name)
        return map


class Seed:

    def __init__(self, *args, **kwargs):
        """
        Args:
            *args: Positional arguments to initialize cell values in order of their definition.
            **kwargs: Keyword arguments to initialize cell values by name.
        """
        self.__dict__.update(wiz=Wiz(self))  # => self.wiz = Wiz(self)
        for name, value in self.__class__.__dict__.items():
            if isinstance(value, Cell):
                self.wiz._name_cell_map[name] = value
                if value.is_key:
                    if self.wiz._key_name != None:
                        raise ValueError(
                            "Only one cell can be defined as key.")
                    self.wiz._key_name = name

        for index, value in enumerate(args):
            name = list(self.wiz._name_cell_map.keys())[index]
            setattr(self, name, value)

        for name, value in kwargs.items():
            if name not in self.wiz._name_cell_map[name]:
                self.wiz._name_cell_map[name] = Cell()
            setattr(self, name, value)

        for name, cell in self.wiz._name_cell_map.items():
            if getattr(self, name) == cell:
                setattr(self, name, cell.default)

    def __setattr__(self, name: str, value: Any):
        """Sets an attribute value, enforcing type checks and checking for frozen attributes.

        Args:
            name (str): The name of the attribute.
            value (Any): The value to be assigned to the attribute.

        Raises:
            AttributeError: If the cell is set to frozen and the value is changed after assignment.
            TypeError: If the value type does not match the expected type defined in the Field.
        """
        if name in self.wiz._name_cell_map:
            cell = self.wiz._name_cell_map[name]
            if cell.frozen and getattr(self, name) != cell:
                msg = (f"The value of attribute `{name}` cannot be modified, "
                       "since it was defined as frozen.")
                raise AttributeError(msg)
            if not isinstance(value, cell.type) and value != None:
                msg = (f"Type mismatch for attribute `{name}`. "
                       f"Expected {cell.type}, got {type(value).__name__}.")
                raise TypeError(msg)
            if cell.auto:
                if getattr(self, name) == cell and value == None:
                    pass
                else:
                    msg = (f"Cannot assign `{value}` to attribute `{name}`, "
                           "since it was defined as auto.")
                    raise AttributeError(msg)
            if cell.is_key and self.wiz.barns:
                for barn in self.wiz.barns:
                    barn._update_key(getattr(self, name), value)
        super().__setattr__(name, value)

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.wiz.name_value_map.items()]
        return "{}({})".format(type(self).__name__, ", ".join(items))


class Barn:

    def __init__(self):
        self._next_autoid = 1
        self._key_seed_map = {}

    def _assign_auto(self, seed: Seed, id: int) -> None:
        for name, cell in seed.wiz._name_cell_map.items():
            if cell.auto and getattr(seed, name) is None:
                seed.__dict__[name] = id

    def _check_key_validity(self, key: Any) -> None:
        if key is None:
            raise ValueError("None is not valid as a key value.")
        elif key in self._key_seed_map:
            raise ValueError(
                f"Key {key} already in use.")

    def add(self, seed: Seed) -> None:
        """Adds a seed to the Barn. Barn keeps insertion order.

        Args:
            seed (Seed): The seed to be added.

        Raises:
            ValueError: If the key value is already in use or is None.
        """
        if seed.wiz.autoid is None:
            seed.wiz.autoid = self._next_autoid
        self._assign_auto(seed, self._next_autoid)
        self._next_autoid += 1
        self._check_key_validity(seed.wiz._key)
        seed.wiz.barns.add(self)
        self._key_seed_map[seed.wiz._key] = seed

    def get(self, key: Any) -> Seed:
        """Retrieves a seed by its key.

        Args:
            key (Any): The key value of the seed.

        Returns:
            seed (Seed): The seed, or None if not found.
        """
        return self._key_seed_map.get(key, None)

    def remove(self, seed: Seed) -> None:
        """Removes a seed from the Barn.

        Args:
            seed (Seed): The seed to be removed.
        """
        del self._key_seed_map[seed.wiz._key]
        seed.wiz.barns.discard(self)

    def _matches_criteria(self, seed: Seed, **kwargs) -> bool:
        """Checks if a seed matches the given criteria.

        Args:
            seed: The object to check.
            **kwargs: Keyword arguments representing cell-value pairs to match.

        Returns:
            bool: True if the seed matches all criteria, False otherwise.
        """
        for cell_name, cell_value in kwargs.items():
            if getattr(seed, cell_name) != cell_value:
                return False
        return True

    def find_all(self, **kwargs) -> "ResultsBarn":
        """Finds all seeds matching the given criteria.

        Args:
            **kwargs: Keyword arguments representing cell-value pairs to match.

        Returns:
            ResultBarn: A Barn of seeds that match the given criteria.
        """
        results = ResultsBarn()
        for seed in self._key_seed_map.values():
            if self._matches_criteria(seed, **kwargs):
                results.add(seed)
        return results

    def find(self, **kwargs) -> Seed:
        """Finds the first seed matching the given criteria.

        Args:
            **kwargs: Keyword arguments representing cell-value pairs to match.

        Returns:
            seed (Seed): The first seed that matches the given criteria, or None if no match is found.
        """
        for seed in self._key_seed_map.values():
            if self._matches_criteria(seed, **kwargs):
                return seed
        return None

    def _update_key(self, old: Any, new: Any) -> None:
        if old == new:
            return
        self._check_key_validity(new)
        old_key_seed_map = self._key_seed_map
        self._key_seed_map = {}
        for key, seed in old_key_seed_map.items():
            if key == old:
                key = new
            self._key_seed_map[key] = seed

    def __len__(self) -> int:
        return len(self._key_seed_map)

    def __repr__(self) -> str:
        count = len(self)
        word = "seed" if count == 1 else "seeds"
        return f"{self.__class__.__name__}({count} {word})"

    def __contains__(self, seed: Seed):
        if seed in self._key_seed_map.values():
            return True
        return False

    def __getitem__(self, index):
        key = list(self._key_seed_map.keys())[index]
        return self._key_seed_map[key]

    def __iter__(self):
        """Iterates over the seeds in the Barn.

        Yields:
            Seed: Each seed in the Barn in insertion order.
        """
        for seed in self._key_seed_map.values():
            yield seed


class ResultsBarn(Barn):
    pass
