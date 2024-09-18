from typing import Any, Type, Optional
from icecream import ic
from .field import Field

# GLOSSARY
# label = field name
# value = field value
# key = primary key value
# keyring = single key or tuple of composite keys


class Dna:
    # seed model
    label_field_map: dict
    key_labels: list
    is_comp_key: bool
    key_defined: bool
    keyring_len: int
    dynamic: bool
    # seed instance
    seed: "Seed"
    autoid: int | None
    keyring: Any | tuple[Any]
    barns: set

    def __init__(self, seed_model: Type["Seed"], seed: Optional["Seed"] = None) -> None:
        self.seed = seed
        self.key_labels = []
        self.label_field_map = {}
        for name, value in seed_model.__dict__.items():
            if not isinstance(value, Field):
                continue
            label = name
            field = value
            field.label = label
            if seed:
                print("field.__dict__", field.__dict__)
                # Make a copy of the field to prevent changes to the original
                field = Field(**field.__dict__, seed=seed, assigned=False)
            self.label_field_map.update({label: field})
            if field.is_key:
                self.key_labels.append(label)
        self.dynamic = False if self.label_field_map else True
        self.key_defined = len(self.key_labels) > 0
        self.is_comp_key = len(self.key_labels) > 1
        self.keyring_len = len(self.key_labels) or 1
        self.seed = seed
        for field in self.label_field_map.values():
            field.assigned = False
        self.autoid = None
        # If the key is not provided, autoid will be used as key
        self.barns = set()

    def _add_dynamic_field(self, label: str):
        """Adds a dynamic field to the Meta object.

        Args:
            label: The label of the dynamic field to add
        """
        assert self.dynamic is True
        field = Field(label=label, seed=self.seed, assigned=False)
        self.label_field_map.update({label: field})

    @property
    def keyring(self) -> Any | tuple[Any]:
        """Returns the keyring of the Seed instance.

        The keyring is either a key or a tuple of keys. If the Meta
        object has no key labels, the autoid is returned instead.

        Returns:
            tuple[Any] or Any: The keyring of the Seed instance
        """
        if not self.key_defined:
            return self.autoid
        keys = [getattr(self.seed, label) for label in self.key_labels]
        if len(keys) == 1:
            return keys[0]
        return tuple(keys)

    def to_dict(self) -> dict[str, Any]:
        """Returns a dictionary representation of the seed.

        The dictionary contains all the fields of the seed, where
        each key is the label of a field and the value is the value of
        that field in the Seed instance.

        Returns:
            dict[str, Any]: A dictionary representing the Seed instance
        """
        return {field.label: field.value for field in self.label_field_map.values()}


class SeedMeta(type):
    def __new__(cls, name, bases, dct):
        ic(name, bases, dct)
        new_class = super().__new__(cls, name, bases, dct)
        new_class.__dna__ = Dna(new_class)
        return new_class


class Seed(metaclass=SeedMeta):
    """The base class for all in-memory data models.

    This class provides common functionality for all data models,
    such as automatic assignment of an autoid, dynamic field creation,
    and dictionary representation of the data model instance.
    """

    def __init__(self, *args, **kwargs):
        """Initialize a Seed-like instance.

        - Positional args are assigned to the seed fields
        in the order they are declared.
        - Static fields kwargs are assigned by name. If the field is not
        defined in the seed-model, a NameError is raised.
        - Dynamic fields kwargs are assigned by name. You can do this if you,
        didn't define any static field in the seed-model.

        After all assignments, the `__post_init__` method is called, if defined.

        Args:
            *args: positional arguments to be assigned to fields
            **kwargs: keyword arguments to be assigned to fields
        """
        # self.__dna__ = Dna(self.__class__, self)
        self.__dict__.update(__dna__=Dna(self.__class__, self))

        fields = list(self.__dna__.label_field_map.values())

        for index, value in enumerate(args):
            field = fields[index]
            setattr(self, field.label, value)

        for label, value in kwargs.items():
            if self.__dna__.dynamic:
                self.__dna__._add_dynamic_field(label)
            elif label not in [field.label for field in fields]:
                raise NameError(f"Field '{label}={value}' was not defined "
                                "in your seed-model. If you have defined "
                                "any static field in the seed-model, "
                                "you cannot use dynamic field creation.")
            setattr(self, label, value)

        for field in fields:
            if not field.assigned:
                setattr(self, field.label, field.default)

        if hasattr(self, "__post_init__"):
            self.__post_init__()

    def __setattr__(self, name: str, value: Any):
        if (field := self.__dna__.label_field_map.get(name)):
            if field.frozen and field.assigned:
                msg = (f"Cannot assign {name}={value}, "
                       "since the field was defined as frozen.")
                raise AttributeError(msg)
            if not isinstance(value, field.type) and value is not None:
                msg = (f"Type mismatch for attribute `{name}`. "
                       f"Expected {field.type}, but got {type(value).__name__}.")
                raise TypeError(msg)
            if field.auto and (field.assigned or (not field.assigned and value is not None)):
                msg = (f"Cannot assign {name}={value}, "
                       "since the field was defined as auto.")
                raise ValueError(msg)
                # if not field.assigned and value is None:
                #     pass
                # else:
                #     msg = (f"Cannot assign {name}={value}, "
                #            "since the field was defined as auto.")
                #     raise AttributeError(msg)
            if not field.none and value is None:
                msg = (f"Cannot assign {name}={value}, "
                       "since the field was defined as none=False.")
                raise ValueError(msg)
            if field.is_key and self.__dna__.barns:
                for barn in self.__dna__.barns:
                    barn._update_key(self, name, value)
            field.assigned = True
        super().__setattr__(name, value)

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.__dna__.to_dict().items()]
        return "{}({})".format(type(self).__name__, ", ".join(items))
