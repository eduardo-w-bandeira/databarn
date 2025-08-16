from typing import Any
from .dna import Dna
# Lazy import: typeguard

# GLOSSARY
# label = field name
# value = field value
# key = primary key value
# keyring = single key or tuple of composite keys


class SeedMeta(type):
    """Sets the __dna__ attribute for the Seed-model."""

    def __new__(klass, name, bases, dikt):
        new_class = super().__new__(klass, name, bases, dikt)
        new_class.__dna__ = Dna(new_class)
        return new_class


class Seed(metaclass=SeedMeta):
    """The base class for all in-memory data models."""

    def __init__(self, *args, **kwargs):
        """Initializes a Seed-like instance.

        - Positional args are assigned to the seed fields
        in the order they were declared in the Seed-model.
        - Static field kwargs are assigned by name. If the field is not
        defined in the seed-model, a NameError is raised.
        - Dynamic field kwargs are assigned by name. You can do this if you
        didn't define any static field in the seed-model.

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
                raise NameError(f"Cannot assign '{label}={value}' because the field"
                                f"'{label}' has not been defined in the seed-model. "
                                "Since at least one static field has been defined in"
                                "the seed-model, dynamic field assignment is not allowed.")
            setattr(self, label, value)

        for field in fields:
            if not field.was_set:
                setattr(self, field.label, field.default)

        if hasattr(self, "__post_init__"):
            self.__post_init__()

    def __setattr__(self, name: str, value: Any):
        if (field := self.__dna__.label_to_field.get(name)):
            if field.type is not Any and value is not None:
                import typeguard  # Lazy import to avoid unecessary import
                try:
                    typeguard.check_type(value, field.type)
                except typeguard.TypeCheckError:
                    raise TypeError(f"Cannot assign '{name}={value}' since the field "
                                    f"was defined as {field.type}, "
                                    f"but got {type(value)}.") from None
            if not field.none and value is None and not field.auto:
                raise ValueError(f"Cannot assign '{name}={value}' since the field "
                                 "was defined as 'none=False'.")
            if field.auto and (field.was_set or (not field.was_set and value is not None)):
                raise AttributeError(f"Cannot assign '{name}={value}' since the field "
                                     "was defined as 'auto=True'.")
            if field.frozen and field.was_set:
                raise AttributeError(f"Cannot assign '{name}={value}' since the field "
                                     "was defined as 'frozen=True'.")
            if field.is_key and self.__dna__.barns:
                raise AttributeError(f"Cannot assign '{name}={value}' since the field "
                                     "was defined as 'key=True' and the seed was appended to a barn.")
            if field.unique and self.__dna__.barns:
                for barn in self.__dna__.barns:
                    barn._check_uniqueness_by_label(field.label, value)
        super().__setattr__(name, value)
        if field:
            field.was_set = True
            self.__dna__._set_parent_if(field)

    def __repr__(self) -> str:
        items = []
        for field in self.__dna__.label_to_field.values():
            items.append(f"{field.label}={field.value!r}")
        in_commas = ", ".join(items)
        return f"{type(self).__name__}({in_commas})"


def dict_to_seed(dikt: dict, trunder_hyphen: bool=False) -> Seed:
    """Recursively converts a dictionary to a Seed-like instance.

    If a value is a list of dictionaries, each dictionary is converted to
    a Seed-like instance and the list is converted to a Barn-like instance.
    
    Args:
        dikt (dict): The dictionary to convert.
        trunder_hyphen (bool): If True, replaces hyphens in keys with triple underscores.
    """
    if not isinstance(dikt, dict):
        raise TypeError(f"Expected a dictionary to convert to Seed, got {type(dikt)} instead.")
    new_dikt = dikt.copy()
    for key, value in dikt.items():
        if trunder_hyphen and "-" in key:
            key = key.replace("-", "___")  # Replace hyphens with triple underscores.
        if isinstance(value, dict):
            seed = dict_to_seed(value)
            new_dikt[key] = seed
        elif isinstance(value, list) and all(isinstance(item, dict) for item in value):
            # If the value is a list of dictionaries, convert each dict to a Seed.
            # Then, create a Barn instance to hold these Seeds.
            from .barn import Barn
            barn = Barn()
            for sub_value in value:
                seed = dict_to_seed(sub_value)
                barn.append(seed)
            new_dikt[key] = barn
    return Seed(**new_dikt)
