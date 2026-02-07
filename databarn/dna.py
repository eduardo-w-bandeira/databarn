from __future__ import annotations
from types import MappingProxyType
from typing import Any, Callable, Type, Iterator
from types import SimpleNamespace as Namespace
import typeguard
from .trails import fo, dual_property, dual_method, classmethod_only, Catalog
from .constants import Sentinel, ABSENT, NO_VALUE
from .exceptions import ConstraintViolationError, GrainTypeMismatchError, CobConsistencyError, StaticModelViolationError, DataBarnViolationError, DataBarnSyntaxError
from .grain import Grain, Grist


class BaseDna:
    """This class is an extension of the Cob-model class,
    which holds the metadata and methods of the model and its cob-objects.
    The intention is to keep the Cob class clean for the user.
    """

    # Model
    model: Type["Cob"]
    label_grain_map: dict[str, Grain]  # {label: Grain}
    grains: tuple[Grain]  # @dual_property
    labels: tuple[str]  # @dual_property
    primakey_labels: list[str]  # @dual_property
    is_compos_primakey: bool  # @dual_property
    primakey_defined: bool  # @dual_property
    primakey_len: int  # @dual_property
    dynamic: bool
    # Changed by the one_to_many_grain decorator
    _outer_model_grain: Grain | None = None

    # Cob object
    cob: "Cob"  # type: ignore
    autoid: int  # If the primakey is not provided, autoid will be used as primakey
    barns: Catalog["Barn"]  # type: ignore # This is an ordered set of Barns
    label_grist_map: dict[str, Grist]  # {label: Grist}
    grists: tuple[Grain]  # @dual_property
    parents: Catalog  # Catalog[Cob] is an ordered set of parent Cobs
    # type: ignore # @dual_property  The cob that has this cob as a child
    latest_parent: "Cob" | None

    @classmethod
    def _setup_class(klass, model: Type["Cob"]) -> None:
        klass.model = model
        klass.label_grain_map = {}
        annotations = getattr(model, "__annotations__", {})
        for label, type in annotations.items():
            attr_value: Grain | Any = getattr(model, label, ABSENT)
            if attr_value is ABSENT:
                grain = Grain()
            elif isinstance(attr_value, Grain):
                grain = attr_value
            else:
                grain = Grain(default=attr_value)
            klass._setup_and_embed_grain(grain, label, type)
        klass.dynamic = False if klass.label_grain_map else True
        # Make the label_grain_map read-only (either dynamic or static model)
        klass.label_grain_map = MappingProxyType(klass.label_grain_map)

    @classmethod
    # Set by decorators
    def _set_outer_model_grain(klass, outer_model_grain: Grain) -> None:
        klass._outer_model_grain = outer_model_grain

    @dual_method
    def _setup_and_embed_grain(owner, grain: Grain, label: str, type: Any) -> None:
        if label in owner.labels:
            raise CobConsistencyError(fo(f"""
                The Grain '{label}' has already been set up in {owner}.label_grain_map."""))
        grain._set_parent_model_metadata(
            parent_model=owner.model, label=label, type=type)
        owner.label_grain_map[label] = grain

    @classmethod_only
    def create_barn(klass) -> "Barn":  # type: ignore
        """Create a new Barn for the model.

        Returns:
            A new Barn object for the model.
        """
        from .barn import Barn  # Lazy import to avoid circular imports
        return Barn(model=klass.model)

    @classmethod_only
    def create_cob_from_dict(klass,
                             dikt: dict,
                             replace_space_with: str | None = "_",
                             replace_dash_with: str | None = "__",
                             suffix_keyword_with: str | None = "_",
                             prefix_leading_num_with: str | None = "n_",
                             replace_invalid_char_with: str | None = "_",
                             suffix_existing_attr_with: str | None = "_",
                             custom_key_converter: Callable | None = None) -> "Cob":  # type: ignore
        """Create a new Cob from a dictionary.

        Args:
            dikt: The dictionary to convert to a Cob.
            replace_space_with: Replace spaces in keys with this string.
            replace_dash_with: Replace dashes in keys with this string.
            suffix_keyword_with: Suffix keywords with this string.
            prefix_leading_num_with: Prefix leading numbers in keys with this string.
            replace_invalid_char_with: Replace invalid characters in keys with this string.
            suffix_existing_attr_with: Suffix existing attributes with this string.
            custom_key_converter: A custom function to convert keys.
        Returns:
            A new Cob object for the model.
        """
        from .funcs import dict_to_cob  # Lazy import to avoid circular imports
        cob = dict_to_cob(
            dikt,
            model=klass.model,
            replace_space_with=replace_space_with,
            replace_dash_with=replace_dash_with,
            suffix_keyword_with=suffix_keyword_with,
            prefix_leading_num_with=prefix_leading_num_with,
            replace_invalid_char_with=replace_invalid_char_with,
            suffix_existing_attr_with=suffix_existing_attr_with,
            custom_key_converter=custom_key_converter,)
        return cob

    @classmethod_only
    def create_cob_from_json(klass,
                             json_str: str,
                             replace_space_with: str | None = "_",
                             replace_dash_with: str | None = "__",
                             suffix_keyword_with: str | None = "_",
                             prefix_leading_num_with: str | None = "n_",
                             replace_invalid_char_with: str | None = "_",
                             suffix_existing_attr_with: str | None = "_",
                             custom_key_converter: Callable | None = None,
                             **json_loads_kwargs) -> "Cob":  # type: ignore
        """Create a new Cob from a JSON string.
        Args:
            json_str: The JSON string to convert to a Cob.
            replace_space_with: Replace spaces in keys with this string.
            replace_dash_with: Replace dashes in keys with this string.
            suffix_keyword_with: Suffix keywords with this string.
            prefix_leading_num_with: Prefix leading numbers in keys with this string.
            replace_invalid_char_with: Replace invalid characters in keys with this string.
            suffix_existing_attr_with: Suffix existing attributes with this string.
            custom_key_converter: A custom function to convert keys.
            **json_loads_kwargs:
                Additional keyword arguments to pass to json.loads()."""
        from .funcs import json_to_cob  # Lazy import to avoid circular imports
        cob = json_to_cob(
            json_str=json_str,
            model=klass.model,
            replace_space_with=replace_space_with,
            replace_dash_with=replace_dash_with,
            suffix_keyword_with=suffix_keyword_with,
            prefix_leading_num_with=prefix_leading_num_with,
            replace_invalid_char_with=replace_invalid_char_with,
            suffix_existing_attr_with=suffix_existing_attr_with,
            custom_key_converter=custom_key_converter,
            **json_loads_kwargs)
        return cob

    @dual_property
    def grains(owner) -> tuple[Grain]:
        """Return a tuple of the grains of the model or cob."""
        return tuple(owner.label_grain_map.values())

    @dual_property
    def labels(owner) -> tuple[str]:
        """Return a tuple of the labels of the model or cob."""
        return tuple(owner.label_grain_map.keys())

    @dual_property
    def primakey_labels(owner) -> tuple[str]:
        """Return a tuple of the primakey labels of the model or cob."""
        labels = [grain.label for grain in owner.grains if grain.pk]
        return tuple(labels)

    @dual_property
    def primakey_defined(owner) -> bool:
        """Return True if the primakey is defined for the model or cob."""
        return (len(owner.primakey_labels) > 0)

    @dual_property
    def is_compos_primakey(owner) -> bool:
        return (len(owner.primakey_labels) > 1)

    @dual_property
    def primakey_len(owner) -> int:
        return (len(owner.primakey_labels) or 1)

    @dual_method
    def get_grain(owner, label: str, default: Any = ABSENT) -> Grain:
        """Return the Grain for the given label.
        If the label does not exist, return the default value if provided,
        otherwise raise a KeyError."""
        if default is ABSENT:
            return owner.label_grain_map[label]
        return owner.label_grain_map.get(label, default)

    # Cob object methods
    def __init__(self, cob: "Cob") -> None:  # type: ignore
        self.cob = cob
        self.autoid = id(cob)  # Default autoid is the id of the cob object
        self.barns = Catalog()
        self.parents = Catalog()
        if self.dynamic:
            # If the model is dynamic, the object-level label_grain_map
            # must be different from the class-level
            self.label_grain_map = {}
        self.label_grist_map = {}
        for grain in self.grains:
            self._create_and_embed_grist(grain)
        if not self.dynamic:
            # Make the label_grist_map read-only (static cob)
            self.label_grist_map = MappingProxyType(self.label_grist_map)

    @property
    def grists(self) -> tuple[Grist]:
        """Return a tuple of Cob's grists."""
        return tuple(self.label_grist_map.values())

    @property
    def active_grists(self) -> tuple[Grist]:
        """Return a tuple of Cob's grists whose values have been set and not been deleted."""
        grists = [grist for grist in self.grists if grist.has_value()]
        return tuple(grists)

    @property
    def primakey_grists(self) -> tuple[Grist]:
        """Return a tuple of the Cob's primakey grists."""
        return tuple(self.get_grist(label) for label in self.primakey_labels)

    @property
    def latest_parent(self) -> "Cob" | None:  # type: ignore
        """Return the latest parent cob if exists, otherwise None.

        CAUTION: If the cob has multiple parents, only the last one is returned.
        """
        if not self.parents:
            return None
        return self.parents[-1]

    def get_grist(self, label: str, default: Any = ABSENT) -> Grist:
        """Returns the grist for the given label.
        If the label does not exist, return the default value if provided,
        otherwise raise a KeyError."""

        if default is ABSENT:
            return self.label_grist_map[label]
        return self.label_grist_map.get(label, default)

    def _create_and_embed_grist(self, grain: Grain) -> Grist:
        """Create a Grist for the given grain in the cob,
        and insert into the label_grist_map."""
        if grain not in self.grains:
            raise CobConsistencyError(fo(f"""
                Cannot create a Grist for the Grain '{grain.label}' because
                it does not exist in the model '{self.model.__name__}'."""))
        if grain.label in self.label_grist_map:
            raise CobConsistencyError(fo(f"""
                Cannot create a Grist for the Grain '{grain.label}' because
                it has already been created in the Cob '{self.model.__name__}'."""))
        grist = Grist(grain, self.cob)
        self.label_grist_map[grist.label] = grist
        return grist

    def _create_cereals_dynamically(self, label: str,
                                   type: Any = Any,
                                   grain: Grain | None = None) -> None:
        """Creates a Grain and its Grist to the dynamic Cob.

        Args:
            label: The label of the dynamic grain to add
            type: The type of the dynamic grain to add
            grain: An optional Grain object to use instead of creating a new one
        """
        if not self.dynamic:
            raise StaticModelViolationError(fo(f"""
                Cannot create the grain '{label}', because the Cob-model is static.
                It is considered static, because at least one grain has been defined
                in the model. Therefore, dynamic grain creation is not allowed."""))
        if label in self.labels:
            raise CobConsistencyError(fo(f"""
                Cannot create the Grain '{label}', because it
                has already been created before."""))
        if grain is None:
            grain = Grain()
        self._setup_and_embed_grain(grain, label, type)
        grist = self._create_and_embed_grist(grain)
        return Namespace(grain=grain, grist=grist)

    def add_grain_dynamically(self, label: str, type: Any, grain: Grain) -> None:
        """Allows the user to add a custom Grain to the dynamic model.
        It also creates the corresponding Grist in the Cob.

        Args:
            label: The label of the dynamic grain to add
            type: The type of the dynamic grain to add
            grain: The Grain object to add
        """
        self._create_cereals_dynamically(label, type, grain)
        grist = self.get_grist(label)
        grist.set_value(None)

    def _remove_cereals_dynamically(self, label: str) -> None:
        """Remove a Grain and its Grist from the dynamic model.

        Args:
            label: The label of the Grain
        """
        if not self.dynamic:
            raise StaticModelViolationError(fo(f"""
                Cannot remove the Grain '{label}' because the Cob-model
                is static and does not allow dynamic Grain deletion."""))
        if label not in self.labels:
            raise KeyError(fo(f"""
                Cannot remove the Grain '{label}', because it
                does not exist in the model."""))
        del self.label_grist_map[label]
        del self.label_grain_map[label]

    def _add_barn(self, barn: "Barn") -> None:  # type: ignore
        self.barns.add(barn)

    def _remove_barn(self, barn: "Barn") -> None:  # type: ignore
        self.barns.remove(barn)

    def get_keyring(self) -> Any | tuple[Any]:
        """'kering' is either a single primakey value or a tuple of
        composite primakey values.

        If the primakey is not defined, 'autoid' is returned instead.

        Returns:
            Any or tuple[Any]: The primakey value(s) of the cob
        """
        if not self.primakey_defined:
            return self.autoid
        primakeys = tuple(grist.get_value() for grist in self.primakey_grists)
        if not self.is_compos_primakey:
            return primakeys[0]
        return primakeys

    def to_dict(self) -> dict[str, Any]:
        """Create a dictionary out of the cob.

        Every sub-Barn is converted into a list of cobs,
        which are then converted to dictionaries recursively.
        Every sub-cob is converted to a dictionary too.
        If key is set for a grain, it is used as the key instead of the label.

        Returns:
            A dictionary representation of the cob
        """
        # Lazy import to avoid circular imports
        from .barn import Barn
        from .cob import Cob
        key_value_map = {}
        for grist in self.grists:
            key = grist.key or grist.label
            grist_value = grist.get_value(default=NO_VALUE)
            if grist_value is NO_VALUE:
                continue  # Skip unset values
            # If value is a barn, recursively process its cobs
            if isinstance(grist_value, Barn):
                barn = grist_value
                dicts = [cob.__dna__.to_dict() for cob in barn]
                key_value_map[key] = dicts
            # Elif value is a cob, convert it to a dict
            elif isinstance(grist_value, Cob):
                key_value_map[key] = grist_value.__dna__.to_dict()
            # Recursively process lists and tuples
            elif isinstance(grist_value, (list, tuple)):
                new_list = []
                for item in grist_value:
                    if isinstance(item, Cob):
                        new_list.append(item.__dna__.to_dict())
                    elif isinstance(item, Barn):
                        new_list.append([cob.__dna__.to_dict()
                                        for cob in item])
                    else:
                        new_list.append(item)
                collection_type: type[list] | type[tuple] = type(grist_value)
                key_value_map[key] = collection_type(new_list)
            else:
                key_value_map[key] = grist_value
        return key_value_map

    def to_json(self, **json_dumps_kwargs) -> str:
        """Returns a JSON string representation of the cob.

        Every sub-Barn is converted into a list of cobs,
        which are then converted to dictionaries recursively.
        Every sub-cob is converted to a dictionary too.

        Args:
            **json_dumps_kwargs:
                Additional keyword arguments to pass to json.dumps().

        Returns:
            A JSON string representation of the cob
        """
        import json  # lazy import to avoid unecessary computation
        return json.dumps(self.to_dict(), **json_dumps_kwargs)

    def _verify_constraints(self, grist: Grist, value: Any) -> None:
        """Checks the value against the grain constraints before setting it.

        Args:
            grist (Grist): The grist to check against.
            value (Any): The value to check and set.

        Returns:
            None
        """
        if grist.type is not Any and value is not None:
            try:
                typeguard.check_type(value, grist.type)
            except typeguard.TypeCheckError:
                raise GrainTypeMismatchError(fo(f"""
                    Cannot assign '{grist.label}={value}' because the Grain
                    was defined as {grist.type}, but got {type(value)}.
                    """)) from None
        if grist.required and value is None and not grist.auto:
            raise ConstraintViolationError(fo(f"""
                Cannot assign '{grist.label}={value}' because the Grain
                was defined as 'required=True'."""))
        if grist.auto and (grist.has_value() or (not grist.has_value() and value is not None)):
            raise ConstraintViolationError(fo(f"""
                Cannot assign '{grist.label}={value}' because the Grain
                was defined as 'auto=True'."""))
        if grist.frozen and grist.has_value():
            raise ConstraintViolationError(fo(f"""
                Cannot assign '{grist.label}={value}' because the Grain
                was defined as 'frozen=True'."""))
        if grist.factory and grist.has_value():
            raise ConstraintViolationError(fo(f"""
                Cannot assign '{grist.label}={value}' because the Grain
                was defined with a 'factory' and can only be set
                internally when the cob is created."""))
        if grist.pk and self.barns:
            raise ConstraintViolationError(fo(f"""
                Cannot assign '{grist.label}={value}' because the Grain
                was defined as 'pk=True' and the cob has been added to a barn."""))
        if grist.unique and self.barns:
            for barn in self.barns:
                barn._check_uniqueness_by_value(grist, value)

    def _add_parent(self, parent: "Cob") -> None:
        self.parents.add(parent)

    def _remove_parent(self, parent: "Cob") -> None:
        self.parents.remove(parent)

    def _set_parent_for_new_value_if(self, grist: Grist):
        # Lazy import to avoid circular imports
        from .barn import Barn
        from .cob import Cob
        value = grist.get_value()
        if isinstance(value, Barn):
            child_barn = value  # Just for clarity
            child_barn._add_parent_cob(self.cob)
        elif isinstance(value, Cob):
            child_cob = value  # Just for clarity
            child_cob.__dna__._add_parent(self.cob)

    def _remove_prev_value_parent_if(self, grist: Grist, new_value: Any) -> None:
        """If the grain was previously set and the value is changing,
        remove parent links if any."""
        if not grist.has_value() or grist.get_value() is new_value:
            return  # No previous value or no change
        # Lazy import to avoid circular imports
        from .barn import Barn
        from .cob import Cob
        old_value = grist.get_value()
        if isinstance(old_value, Barn):
            child_barn = old_value  # Just for clarity
            # Remove the parent for the barn
            child_barn._remove_parent_cob(self.cob)
        elif isinstance(old_value, Cob):
            child_cob = old_value  # Just for clarity
            child_cob.__dna__._remove_parent(self.cob)

    def _check_and_get_comparables(self, cob: "Cob") -> list[Grist]:
        if not isinstance(cob, self.model):
            raise CobConsistencyError(fo(f"""
                Cannot compare this Cob '{self.model.__name__}' with
                '{type(cob).__name__}', because they are different types."""))
        comparables = [grist for grist in self.grists if grist.comparable]
        if not comparables:
            raise CobConsistencyError(fo(f"""
                Cannot compare Cob '{self.model.__name__}' objects because
                none of its grains are marked as comparable.
                To enable comparison, set comparable=True on at least one grain."""))
        return comparables

    # dict-like methods
    def items(self) -> Iterator[tuple[str, Any]]:
        for grist in self.active_grists:
            yield grist.label, grist.get_value()

    def keys(self) -> Iterator[str]:
        for grist in self.active_grists:
            yield grist.label

    def values(self) -> Iterator[Any]:
        for grist in self.active_grists:
            yield grist.get_value()

    def clear(self) -> None:
        """Remove all values from the cob."""
        # Only delete grains that currently have values
        for grist in self.active_grists:
            del self.cob[grist.label]

    def copy(self) -> "Cob":  # type: ignore
        """Create a shallow copy of the Cob."""
        raise NotImplementedError(fo(f"""
            The 'copy' method is not implemented yet for Cob objects."""))
    
    def fromkeys(self, seq, value) -> "Cob":  # type: ignore
        """That function that no one uses."""
        dikt = {}
        for key in seq:
            dikt[key] = value
        return self.model(**dikt)

    def get(self, key: str, default: Any = ABSENT) -> Any:
        if key in self.labels:
            return self.cob[key]
        if default is ABSENT:
            raise KeyError(fo(f"""
                The key '{key}' does not exist in the cob."""))
        return default

    def pop(self, key: str, default: Any = ABSENT) -> Any:
        if key in self.labels:
            value = self.cob[key]
            del self.cob[key]
            return value
        if default is ABSENT:
            raise KeyError(fo(f"""
                The key '{key}' does not exist in the cob."""))
        return default

    def popitem(self) -> tuple[str, Any]:
        """Removes the key and value of last defined Grain.

        Returns:
            A tuple of (key, value) of the removed attribute.
            Raises KeyError if the Cob is empty.
        """
        if not self.active_grists:
            raise KeyError(fo(f"""The Cob '{self.model.__name__}' is empty."""))
        last_grist = self.active_grists[-1]
        value = last_grist.get_value()  # Get value before deletion
        del self.cob[last_grist.label]
        return last_grist.label, value

    def setdefault(self, key: str, default: Any = None) -> Any:
        """If the key is in the cob, return its value.
        Otherwise, set it to the default value and return the default value.
        """
        if key in self.labels:
            return self.cob[key]
        self.cob[key] = default
        return default


    def update(self, other: dict | Sentinel = ABSENT, /, **kwargs) -> None:
        if other is not ABSENT:
            if type(other) is dict:
                for key in other.keys():
                    self.cob[key] = other[key]
            else:
                for key, value in other:
                    self.cob[key] = value
        for key, value in kwargs.items():
            self.cob[key] = value

    def values(self) -> Iterator[Any]:
        for grist in self.active_grists:
            yield grist.get_value()


def dna_factory(model: Type["Cob"]) -> Type["Dna"]:  # type: ignore
    """Dna class factory function."""
    class Dna(BaseDna):
        pass
    Dna._setup_class(model)
    return Dna
