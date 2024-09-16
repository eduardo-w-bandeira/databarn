from typing import Any
from .field import Field, Meta
# from .simplidatabarn import _Branches

# GLOSSARY
# label = field name
# value = field value
# key = primary key value
# keyring = key or a tuple of composite keys

seedmodel_meta = {}


def make_meta(seed_model: "Seed") -> Meta:
    """Extract metadata from a Seed-derived class.

    Args:
        seed_model: Seed-derived class

    Returns:
        Meta: Meta(_Seed) object
    """
    key_labels = []
    fields = {}
    for label, field in seed_model.__dict__.items():
        if isinstance(field, Field):
            field.label = label
            fields[label] = field
            if field.is_key:
                key_labels.append(label)
    dynamic = False if fields else True
    meta = Meta(seed_model=seed_model,
                fields=fields,
                key_labels=key_labels,
                key_defined=len(key_labels) > 0,
                is_comp_key=len(key_labels) > 1,
                keyring_len=len(key_labels) or 1,
                dynamic=dynamic)
    return meta


def get_or_make_meta(seed_model: "Seed") -> Meta:
    if seed_model not in seedmodel_meta:
        meta = make_meta(seed_model)
        seedmodel_meta[seed_model] = meta
    return seedmodel_meta[seed_model]


class Dna():
    """Object that stores metadata and provides some utility methods for a Seed instance.

    Attributes:
        meta: Meta object associated with the Seed-derived class
        _seed: Seed instance that owns this Dna
        _unassigned_labels: set of labels that have not been assigned a value yet
        autoid: unique identifier for the Seed instance
    """

    def __init__(self, seed: "Seed"):
        self._seed = seed
        self.meta = get_or_make_meta(seed.__class__)
        if self.meta.dynamic:
            # Create a new object, so fields can be appended
            self.meta = make_meta(seed.__class__)
        self._unassigned_labels = set(
            field.label for field in self.meta.fields.values())
        self.autoid: int | None = None
        # If the key is not provided, autoid will be used as key
        self.barns = set()

    def _add_dynamic_field(self, label: str):
        """Adds a dynamic field to the Meta object.

        Args:
            label: The label of the dynamic field to add
        """
        assert self.meta.dynamic is True
        field = Field()
        field.label = label
        self.meta.fields[label] = field
        self._unassigned_labels.add(field.label)

    @property
    def keyring(self) -> Any | tuple[Any]:
        """Returns the keyring of the Seed instance.

        The keyring is either a key or a tuple of keys. If the Meta
        object has no key labels, the autoid is returned instead.

        Returns:
            tuple[Any] or Any: The keyring of the Seed instance
        """
        if not self.meta.key_defined:
            return self.autoid
        keys = [getattr(self._seed, label) for label in self.meta.key_labels]
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
        labels = [field.label for field in self.meta.fields.values()]
        return {label: getattr(self._seed, label) for label in labels}


class Seed:
    """The base class for all in-memory data models.

    This class provides common functionality for all data models,
    such as automatic assignment of an autoid, dynamic field creation,
    and dictionary representation of the data model instance.
    """

    def __init__(self, *args, **kwargs):
        """Initialize a Seedish instance.

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
        self.__dict__.update(__dna__=Dna(self))  # => self.__dna__ = Dna(self)

        labels = [field.label for field in self.__dna__.meta.fields.values()]

        for index, value in enumerate(args):
            label = labels[index]
            setattr(self, label, value)

        for label, value in kwargs.items():
            if self.__dna__.meta.dynamic:
                self.__dna__._add_dynamic_field(label)
            elif label not in labels:
                raise NameError(f"Field '{label}={value}' was not defined "
                                "in your seed-model. If you have defined "
                                "any static field in the seed-model, "
                                "you cannot use dynamic field creation.")
            setattr(self, label, value)

        for label in list(self.__dna__._unassigned_labels):
            field = self.__dna__.meta.fields.get(label)
            setattr(self, label, field.default)

        if hasattr(self, "__post_init__"):
            self.__post_init__()

    def __setattr__(self, name: str, value: Any):
        """Sets an attribute of the Seed instance.

        The attribute is set if and only if it is a field of the Seed class.
        If the attribute is a field and it was not previously assigned,
        it is assigned now. If it was previously assigned and the field
        is frozen, an AttributeError is raised. If it was previously
        assigned and the field is not frozen, the attribute is updated.

        If the attribute is not a field of the Seed class, the attribute
        is added to the Seed instance as a dynamic field if the Meta
        object of the Seed class has dynamic set to True.

        If the attribute is a field of the Seed class and the field is
        a key, the key is updated in any Barn that the Seed instance
        belongs to.

        Args:
            name (str): The name of the attribute to set.
            value (Any): The value to assign to the attribute.
        """
        if (field := self.__dna__.meta.fields.get(name)):
            was_assigned = name not in self.__dna__._unassigned_labels
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
