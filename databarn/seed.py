from typing import Any
from .dna import Dna

# GLOSSARY
# label = field name
# value = field value
# key = (primary) key value
# keyring = single key or tuple of composite keys


class SeedMeta(type):
    """Sets the __dna__ attribute for the Seed-model."""

    def __new__(cls, name, bases, dct):
        new_class = super().__new__(cls, name, bases, dct)
        new_class.__dna__ = Dna(new_class)
        return new_class


class Seed(metaclass=SeedMeta):
    """The base class for all in-memory data models."""

    def __init__(self, *args, **kwargs):
        """Initializes a Seed-like instance.

        - Positional args are assigned to the seed fields
        in the order they were declared in the Seed-model.
        - Static field kwargs are assigned by name. If the field is not
        defined in the Seed-model, a NameError is raised.
        - Dynamic field kwargs are assigned by name. You can do this if you
        didn't define any static field in the Seed-model.

        After all assignments, the `__post_init__` method is called, if defined.

        Args:
            *args: positional args to be assigned to fields
            **kwargs: keyword args to be assigned to fields
        """
        # self.__dna__ = Dna(self.__class__, self)
        self.__dict__.update(__dna__=Dna(self.__class__, self))

        fields = list(self.__dna__.label_to_field.values())

        for index, value in enumerate(args):
            field = fields[index]
            setattr(self, field.label, value)

        for label, value in kwargs.items():
            if self.__dna__.dynamic:
                self.__dna__._create_dynamic_field(label)
            elif label not in self.__dna__.label_to_field:
                raise NameError(f"Field '{label}={value}' was not defined "
                                "in your seed-model. If you have defined "
                                "any static field in the seed-model, "
                                "you cannot use dynamic field creation.")
            setattr(self, label, value)

        for field in fields:
            if not field.was_set:
                setattr(self, field.label, field.default)

        if hasattr(self, "__post_init__"):
            self.__post_init__()

    def __setattr__(self, name: str, value: Any):
        if (field := self.__dna__.label_to_field.get(name)):
            if not isinstance(value, field.type) and value is not None:
                mes = (f"Cannot assign {name}={value} since the field "
                       f"was defined as type={field.type}, "
                       f"but got {type(value).__name__}.")
                raise TypeError(mes)
            if not field.none and value is None:
                mes = (f"Cannot assign {name}={value} since the field "
                       "was defined as none=False.")
                raise ValueError(mes)
            if field.frozen and field.was_set:
                mes = (f"Cannot assign {name}={value} since the field "
                       "was defined as frozen=True.")
                raise AttributeError(mes)
            if field.auto and (field.was_set or (not field.was_set and value is not None)):
                mes = (f"Cannot assign {name}={value} since the field "
                       "was defined as auto=True.")
                raise AttributeError(mes)
            if field.is_key and self.__dna__.barns:
                mes = (f"Cannot assign {name}={value} since the field "
                       "was defined as key=True and the seed was appended to a barn.")
                raise AttributeError(mes)
            field.was_set = True
        super().__setattr__(name, value)

    def __repr__(self) -> str:
        items = [f"{k}={v!r}" for k, v in self.__dna__.to_dict().items()]
        return "{}({})".format(type(self).__name__, ", ".join(items))
