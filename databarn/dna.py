from __future__ import annotations
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from types import MappingProxyType
from typing import Any, TYPE_CHECKING, get_origin, get_args
from types import SimpleNamespace as Namespace
from beartype.door import is_bearable
from beartype.roar import BeartypeDecorHintForwardRefException
from .trails import fo, dual_property, dual_method, classmethod_only, Catalog
from .constants import Sentinel, ABSENT
from .exceptions import CobConstraintViolationError, GrainTypeMismatchError, CobConsistencyError, StaticModelViolationError, DataBarnViolationError, DataBarnSyntaxError
from .grain import Grain, Grist

if TYPE_CHECKING:
    from .cob import Cob
    from .barn import Barn


class BaseDna:
    """This class is an extension of the Cob-model class,
    which holds the metadata and methods of the model and its cob-objects.
    The intention is to keep the Cob class clean for the user.
    """

    @staticmethod
    def _type_display_name(type_hint: Any) -> str:
        """Return a user-facing type name for error messages."""
        if isinstance(type_hint, type):
            return type_hint.__name__
        forward_arg = getattr(type_hint, "__forward_arg__", None)
        if isinstance(forward_arg, str):
            return forward_arg
        if isinstance(type_hint, str):
            return type_hint
        return str(type_hint)

    @staticmethod
    def _barn_model_matches(expected_model_type: Any, actual_model_type: type[Any]) -> bool:
        """Compare Barn model type args while tolerating unresolved forward references."""
        if isinstance(expected_model_type, type):
            return actual_model_type is expected_model_type
        expected_name = BaseDna._type_display_name(expected_model_type)
        expected_short_name = expected_name.split(".")[-1]
        return actual_model_type.__name__ == expected_short_name

    # Model
    model: type["Cob"]
    label_grain_map: Mapping[str, Grain]  # {label: Grain}
    dynamic: bool
    # Changed by the one_to_many_grain decorator
    _outer_model_grain: Grain | None = None

    # Cob instance
    cob: "Cob"  # type: ignore
    autoid: int  # If the primakey is not provided, autoid will be used as primakey
    barns: Catalog["Barn"]  # type: ignore # This is an ordered set of Barns
    label_grist_map: dict[str, Grain] | Mapping[str, Grist]  # {label: Grist}
    parents: Catalog  # Catalog[Cob] is an ordered set of parent Cobs

    @classmethod
    def __setup__(klass, model: type["Cob"]) -> None:
        klass.model = model
        klass.label_grain_map = {}
        annotations: dict[str, Any] = getattr(model, "__annotations__", {})
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
    def _validate_grain(owner, grain: Grain) -> None:
        if grain.autoenum and not issubclass(grain.type, int):  # type: ignore
            raise DataBarnSyntaxError(fo(f"""
                The Grain '{grain.label}' was defined as 'autoenum=True',
                but was type annotated as {grain.type}.
                'autoenum' only works with 'int' or compatible types."""))

    @dual_method
    def _setup_and_embed_grain(owner, grain: Grain, label: str, type: Any) -> None:
        if label in owner.labels:
            raise CobConsistencyError(fo(f"""
                The Grain '{label}' has already been
                set up in {owner}.label_grain_map."""))
        grain._set_parent_model_metadata(
            parent_model=owner.model, label=label, type=type)
        owner._validate_grain(grain)
        owner.label_grain_map[label] = grain  # type: ignore

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
                             # type: ignore
                             custom_key_converter: Callable[[Any], str] | None = None) -> "Cob":
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
                             custom_key_converter: Callable[[
                                 Any], str] | None = None,
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
    def grains(owner) -> tuple[Grain, ...]:
        """Return a tuple of the grains of the model or cob."""
        return tuple(owner.label_grain_map.values())

    @dual_property
    def labels(owner) -> tuple[str, ...]:
        """Return a tuple of the labels of the model or cob."""
        return tuple(owner.label_grain_map.keys())

    @dual_property
    def primakey_labels(owner) -> tuple[str, ...]:
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
    def get_grain(owner, label: str, default: Any = None) -> Grain | Any:
        """Returns the grain for the given label.
        If the label does not exist, returns the default."""
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
    def grists(self) -> tuple[Grist, ...]:
        """Return a tuple of Cob's grists."""
        return tuple(self.label_grist_map.values())

    @property
    def active_grists(self) -> tuple[Grist, ...]:
        """Return a tuple of Cob's grists whose values have been set and not been deleted."""
        grists = [grist for grist in self.grists if grist.attr_exists()]
        return tuple(grists)

    @property
    def primakey_grists(self) -> tuple[Grist, ...]:
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

    def get_grist(self, label: str, default: Any = None) -> Grist | Any:
        """Returns the grist for the given label.
        If the label does not exist, return the default."""
        return self.label_grist_map.get(label, default)

    def get_active_grist(self, label: str, default: Any = None) -> Grist | Any:
        """Returns the grist for the given label if it exists and has a value,
        otherwise returns the default."""
        grist = self.get_grist(label, default=None)
        if grist and grist.attr_exists():
            return grist
        return default

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
                                    grain: Grain | None = None) -> Namespace:
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

        Args:
            label: The label of the dynamic grain to add
            type: The type of the dynamic grain to add
            grain: The Grain object to add
        """
        self._create_cereals_dynamically(label, type, grain)

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

    def get_keyring(self) -> Any | tuple[Any, ...] | Sentinel:
        """Retrieves the primary key(s) for the current object.
        Returns:
            Any: The primary key value if a single primary key is defined.
            tuple[Any, ...]: A tuple of primary key values if a composite primary key is defined.
            Sentinel: Returns ABSENT if any primary key attribute does not exist.
        Notes:
            - If the primary key is not defined, returns 'autoid' (the Cob's auto-generated ID).
            - If any required primary key attribute is missing, returns ABSENT.
            - For composite primary keys, returns a tuple of all primary key values.
        """
        if not self.primakey_defined:
            return self.autoid
        primakeys = []
        for grist in self.primakey_grists:
            if not grist.attr_exists():
                return ABSENT
            primakeys.append(grist.get_value())
        if not self.is_compos_primakey:
            return primakeys[0]
        return tuple(primakeys)

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
            grist_value = grist.get_value(default=ABSENT)
            if grist_value is ABSENT:
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
                collection_type: type[list[Any]] | type[tuple[Any, ...]] = type(
                    grist_value)
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
        if grist.type is not Any:
            bearable = False
            try:
                bearable = is_bearable(value, grist.type)
            except BeartypeDecorHintForwardRefException as exc:
                # Postponed/quoted forward references can fail to resolve in beartype.
                # Keep DataBarn's exception surface stable for callers.
                from .barn import Barn  # Lazy import to avoid circular imports
                if get_origin(grist.type) is Barn and isinstance(value, Barn):
                    bearable = True
                else:
                    raise GrainTypeMismatchError(fo(f"""
                        Cannot assign '{grist.label}={value}' because the Grain
                        type '{grist.type}' could not be resolved ({exc.__class__.__name__}).""")) from exc
            if not bearable:
                raise GrainTypeMismatchError(fo(f"""
                    Cannot assign '{grist.label}={value}' because the Grain
                    was defined as {grist.type}, but got {type(value)}."""))
            from .barn import Barn  # Lazy import to avoid circular imports
            origin_type = get_origin(grist.type)
            if origin_type is Barn:
                type_args = get_args(grist.type)
                if type_args:
                    expected_model_type = type_args[0]
                    if not self._barn_model_matches(expected_model_type, value.model):
                        expected_model_name = self._type_display_name(
                            expected_model_type)
                        raise GrainTypeMismatchError(fo(f"""
                            Cannot assign '{grist.label}={value}' because the Grain
                            was defined as 'Barn[{expected_model_name}]',
                            but got 'Barn[{value.model.__name__}]'."""))
        if grist.frozen and grist.attr_exists():
            raise CobConstraintViolationError(fo(f"""
                Cannot assign '{grist.label}={value}' because the Grain
                was defined as 'frozen=True'."""))
        if grist.pk and self.barns:
            raise CobConstraintViolationError(fo(f"""
                Cannot assign '{grist.label}={value}' because the Grain
                was defined as 'pk=True' and the Cob has been added to a barn."""))
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
        if not grist.attr_exists() or grist.get_value() is new_value:
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

    def clear(self) -> None:
        """Remove all values from the cob."""
        # Only delete grains that currently have values
        for grist in self.grists:
            if grist.attr_exists():
                del self.cob[grist.label]

    def copy(self) -> "Cob":  # type: ignore
        """Create a shallow copy of the Cob."""
        raise NotImplementedError(fo(f"""
            The 'copy' method is not implemented yet for Cob objects."""))

    def fromkeys(self, seq: Sequence[str], value: Any) -> "Cob":
        """That function that no one uses."""
        dikt: dict[str, Any] = {}
        for key in seq:
            dikt[key] = value
        return self.model(**dikt)

    def get(self, key: str, default: Any = None) -> Any:
        grist = self.get_active_grist(key, default=None)
        if grist:
            return grist.get_value()
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
            raise KeyError(
                fo(f"""The Cob '{self.model.__name__}' is empty."""))
        last_grist = self.active_grists[-1]
        value = last_grist.get_value()  # Get value before deletion
        del self.cob[last_grist.label]
        return last_grist.label, value

    def setdefault(self, key: str, default: Any = None) -> Any:
        """If the key is in the cob, return its value.
        Otherwise, set it to the default value and return the default value.
        """
        grist = self.get_active_grist(key, default=None)
        if grist:
            return grist.get_value()
        self.cob[key] = default
        return default

    def update(self,
               other: Mapping[str, Any] | Iterable[tuple[Any, Any]] | Sentinel = ABSENT,
               /,
               **kwargs: Any,) -> None:
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


def create_dna_class(model: type["Cob"]) -> type[BaseDna]:
    """Dna class factory function."""
    class Dna(BaseDna):
        pass
    Dna.__setup__(model)
    return Dna
