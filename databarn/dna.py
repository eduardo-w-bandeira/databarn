from __future__ import annotations
from .trails import fo, dual_property, dual_method, classmethod_only, Catalog
from .constants import UNSET
from .exceptions import ConstraintViolationError, GrainTypeMismatchError, CobConsistencyError, StaticModelViolationError, DataBarnViolationError, DataBarnSyntaxError
from .grain import Grain, Seed
from types import MappingProxyType
from typing import Any, Callable, Type, Iterator


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
    # Changed by the create_child_barn_grain decorator
    _outer_model_grain: Grain | None = None

    # Cob object
    cob: "Cob"
    autoid: int  # If the primakey is not provided, autoid will be used as primakey
    barns: Catalog  # Catalog[Barn] is an ordered set of Barns
    label_seed_map: dict[str, Seed]  # {label: Seed}
    seeds: tuple[Grain]  # @dual_property
    parents: Catalog  # Catalog[Cob] is an ordered set of parent Cobs
    parent: "Cob" | None  # @dual_property  The cob that has this cob as a child

    @classmethod
    def _set_up_class(klass, model: Type["Cob"]) -> None:
        klass.model = model
        klass.label_grain_map = {}
        annotations = getattr(model, "__annotations__", {})
        for label, type in annotations.items():
            grain_or_default: Grain | Any = getattr(model, label, UNSET)
            if isinstance(grain_or_default, Grain):
                grain = grain_or_default
            elif grain_or_default is UNSET:
                grain = Grain()
            else:
                grain = Grain(default=grain_or_default)
            klass._set_up_grain(grain, label, type)
        klass.dynamic = False if klass.label_grain_map else True
        # Make the label_grain_map read-only (either dynamic or static model)
        klass.label_grain_map = MappingProxyType(klass.label_grain_map)

    @classmethod
    # Set by decorators
    def _set_outer_model_grain(klass, outer_model_grain: Grain) -> None:
        klass._outer_model_grain = outer_model_grain

    @dual_method
    def _set_up_grain(dna, grain: Grain, label: str, type: Any) -> None:
        if label in dna.labels:
            raise DataBarnViolationError(fo(f"""
                Unexpected error while setting up the grain '{label}'.
                The grain '{label}' has already been set up in {dna}.label_grain_map."""))
        grain._set_model_attrs(
            model=dna.model, label=label, type=type)
        dna.label_grain_map[label] = grain

    @classmethod_only
    def create_barn(klass) -> "Barn":  # type: ignore
        """Create a new Barn for the model.

        Returns:
            A new Barn object for the model.
        """
        from .barn import Barn  # Lazy import to avoid circular imports
        return Barn(model=klass.model)

    @classmethod_only
    def dict_to_cob(klass,
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

    @dual_property
    def grains(dna) -> tuple[Grain]:
        """Return a tuple of the grains of the model or cob."""
        return tuple(dna.label_grain_map.values())

    @dual_property
    def labels(dna) -> tuple[str]:
        """Return a tuple of the labels of the model or cob."""
        return tuple(dna.label_grain_map.keys())

    @dual_property
    def primakey_labels(dna) -> tuple[str]:
        """Return a tuple of the primakey labels of the model or cob."""
        labels = [grain.label for grain in dna.grains if grain.pk]
        return tuple(labels)

    @dual_property
    def primakey_defined(dna) -> bool:
        """Return True if the primakey is defined for the model or cob."""
        return (len(dna.primakey_labels) > 0)

    @dual_property
    def is_compos_primakey(dna) -> bool:
        return (len(dna.primakey_labels) > 1)

    @dual_property
    def primakey_len(dna) -> int:
        return (len(dna.primakey_labels) or 1)

    @dual_method
    def get_grain(dna, label: str, default: Any = UNSET) -> Grain:
        """Return the grain for the given label.
        If the label does not exist, return the default value if provided,
        otherwise raise a KeyError."""
        if default is UNSET:
            return dna.label_grain_map[label]
        return dna.label_grain_map.get(label, default)

    def __init__(self, cob: "Cob") -> None:
        self.cob = cob
        self.autoid = id(cob)  # Default autoid is the id of the cob object
        self.barns = Catalog()
        self.parents = Catalog()
        if self.dynamic:
            # Since the model is dynamic, the object-level grain map...
            # has to be different from the class-level
            self.label_grain_map = {}
        self.label_seed_map = {}
        for grain in self.grains:
            self._set_up_seed(grain)
        if not self.dynamic:
            # Make the label_seed_map read-only if the model is static
            self.label_seed_map = MappingProxyType(self.label_seed_map)

    @property
    def seeds(self) -> tuple[Seed]:
        """Return a tuple of the cob's seeds."""
        return tuple(self.label_seed_map.values())

    @property
    def primakey_seeds(self) -> tuple[Seed]:
        """Return a tuple of the cob's primakey seeds."""
        return tuple(self.get_seed(label) for label in self.primakey_labels)

    @property
    def parent(self) -> "Cob" | None:
        """Return the first parent cob if exists, otherwise None.

        CAUTION: If the cob has multiple parents, only the first one is returned.
        """
        if not self.parents:
            return None
        return self.parents[0]

    def _set_up_seed(self, grain: Grain) -> None:
        """Set up a seed for the given grain in the cob."""
        seed = Seed(grain, self.cob, init_with_sentinel=True)
        self.label_seed_map[seed.label] = seed

    def items(self) -> Iterator[tuple[str, Any]]:
        for label, seed in self.label_seed_map.items():
            yield label, seed.get_value()

    def get_seed(self, label: str, default: Any = UNSET) -> Seed:
        """Return the seed for the given label.
        If the label does not exist, return the default value if provided,
        otherwise raise a KeyError."""
        if default is UNSET:
            return self.label_seed_map[label]
        return self.label_seed_map.get(label, default)

    def add_grain_dynamically(self, label: str, type: Any = Any, grain: Grain | None = None) -> None:
        """Add a grain and its seed to the dynamic model.

        Args:
            label: The label of the dynamic grain to add

        Returns:
            The created grain object"""
        if not self.dynamic:
            raise StaticModelViolationError(fo(f"""
                Cannot create the grain '{label}', because the Cob-model is static.
                It is considered static, because at least one grain has been defined
                in the model. Therefore, dynamic grain creation is not allowed."""))
        if label in self.labels:
            raise CobConsistencyError(fo(f"""
                Cannot create the grain '{label}', because it
                has already been created before."""))
        if grain is None:
            grain = Grain()
        self._set_up_grain(grain, label, type)
        self._set_up_seed(grain)

    def _remove_grain_dynamically(self, label: str) -> None:
        """Remove a grain and its seed from the dynamic model.

        Args:
            label: The label of the dynamic grain to remove
        """
        if not self.dynamic:
            raise StaticModelViolationError(fo(f"""
                Cannot remove grain '{label}' because the Cob-model
                is static and does not allow dynamic grain deletion."""))
        if label not in self.labels:
            raise KeyError(fo(f"""
                Cannot remove the grain '{label}', because it
                does not exist in the model."""))
        del self.label_grain_map[label]
        del self.label_seed_map[label]

    def _add_barn(self, barn: "Barn") -> None:
        self.barns.add(barn)

    def _remove_barn(self, barn: "Barn") -> None:
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
        primakeys = tuple(seed.get_value() for seed in self.primakey_seeds)
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
        for seed in self.seeds:
            key = seed.key or seed.label
            seed_value = seed.get_value()
            # If value is a barn, recursively process its cobs
            if isinstance(seed_value, Barn):
                barn = seed_value
                dicts = [cob.__dna__.to_dict() for cob in barn]
                key_value_map[key] = dicts
            # Elif value is a cob, convert it to a dict
            elif isinstance(seed_value, Cob):
                key_value_map[key] = seed_value.__dna__.to_dict()
            # Recursively process lists and tuples
            elif isinstance(seed_value, (list, tuple)):
                new_list = []
                for item in seed_value:
                    if isinstance(item, Cob):
                        new_list.append(item.__dna__.to_dict())
                    elif isinstance(item, Barn):
                        new_list.append([cob.__dna__.to_dict()
                                        for cob in item])
                    else:
                        new_list.append(item)
                collection_type: type[list] | type[tuple] = type(seed_value)
                key_value_map[key] = collection_type(new_list)
            else:
                key_value_map[key] = seed_value
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

    def _verify_constraints(self, seed: Seed, value: Any) -> None:
        """Checks the value against the grain constraints before setting it.

        Args:
            seed (Seed): The seed to check against.
            value (Any): The value to check and set.

        Returns:
            None
        """
        if seed.type is not Any and value is not None:
            import typeguard  # Lazy import to avoid unecessary computation
            try:
                typeguard.check_type(value, seed.type)
            except typeguard.TypeCheckError:
                raise GrainTypeMismatchError(fo(f"""
                    Cannot assign '{seed.label}={value}' because the grain
                    was defined as {seed.type}, but got {type(value)}.
                    """)) from None
        if seed.required and value is None and not seed.auto:
            raise ConstraintViolationError(fo(f"""
                Cannot assign '{seed.label}={value}' because the grain 
                was defined as 'required=True'."""))
        if seed.auto and (seed.has_been_set or (not seed.has_been_set and value is not None)):
            raise ConstraintViolationError(fo(f"""
                Cannot assign '{seed.label}={value}' because the grain
                was defined as 'auto=True'."""))
        if seed.frozen and seed.has_been_set:
            raise ConstraintViolationError(fo(f"""
                Cannot assign '{seed.label}={value}' because the grain
                was defined as 'frozen=True'."""))
        if seed.factory and seed.has_been_set:
            raise ConstraintViolationError(fo(f"""
                Cannot assign '{seed.label}={value}' because the grain
                was defined with a 'factory' and can only be set
                internally when the cob is created."""))
        if seed.pk and self.barns:
            raise ConstraintViolationError(fo(f"""
                Cannot assign '{seed.label}={value}' because the grain
                was defined as 'pk=True' and the cob has been added to a barn."""))
        if seed.unique and self.barns:
            for barn in self.barns:
                barn._check_uniqueness_by_value(seed, value)

    def _add_parent(self, parent: "Cob") -> None:
        self.parents.add(parent)

    def _remove_parent(self, parent: "Cob") -> None:
        self.parents.remove(parent)

    def _set_parent_for_new_value_if(self, seed: Seed):
        # Lazy import to avoid circular imports
        from .barn import Barn
        from .cob import Cob
        value = seed.get_value()
        if isinstance(value, Barn):
            child_barn = value  # Just for clarity
            child_barn._add_parent_cob(self.cob)
        elif isinstance(value, Cob):
            child_cob = value  # Just for clarity
            child_cob.__dna__._add_parent(self.cob)

    def _remove_prev_value_parent_if(self, seed: Seed, new_value: Any) -> None:
        """If the grain was previously set and the value is changing,
        remove parent links if any."""
        if not seed.has_been_set or seed.get_value() is new_value:
            return  # No previous value or no change
        # Lazy import to avoid circular imports
        from .barn import Barn
        from .cob import Cob
        old_value = seed.get_value()
        if isinstance(old_value, Barn):
            child_barn = old_value  # Just for clarity
            # Remove the parent for the barn
            child_barn._remove_parent_cob(self.cob)
        elif isinstance(old_value, Cob):
            child_cob = old_value  # Just for clarity
            child_cob.__dna__._remove_parent(self.cob)

    def _check_and_get_comparables(self, cob: "Cob") -> list[Seed]:
        if not isinstance(cob, self.model):
            raise CobConsistencyError(fo(f"""
                Cannot compare this Cob '{self.model.__name__}' with
                '{type(cob).__name__}', because they are different types."""))
        comparables = [seed for seed in self.seeds if seed.comparable]
        if not comparables:
            raise CobConsistencyError(fo(f"""
                Cannot compare Cob '{self.model.__name__}' objects because
                none of its grains are marked as comparable.
                To enable comparison, set comparable=True on at least one grain."""))
        return comparables


def dna_factory(model: Type["Cob"]) -> Type["Dna"]:
    """Dna class factory function."""
    class Dna(BaseDna):
        pass
    Dna._set_up_class(model)
    return Dna
