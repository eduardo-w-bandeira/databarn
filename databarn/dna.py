from __future__ import annotations
from .trails import fo, dual_property, dual_method, sentinel
from .exceptions import ConsistencyError, GrainTypeMismatchError, ComparisonNotSupportedError
from .grain import Grain, Seed
from typing import Any, Type, get_type_hints


def create_dna(model: Type["Cob"]) -> Type["Dna"]:
    """Dna class factory function."""

    class Dna:
        """This class is an extension of the Cob-model class,
        which holds the metadata and methods of the model and its cob-objects.
        The intention is to keep the Cob class clean for the user.
        """

        # Model
        model: Type["Cob"]
        label_grain_map: dict[str, Grain] = {}  # {label: Grain}
        grains: tuple[Grain]  # @dual_property
        labels: tuple[str]  # @dual_property
        primakey_labels: list[str]  # @dual_property
        is_compos_primakey: bool  # @dual_property
        primakey_defined: bool  # @dual_property
        primakey_len: int  # @dual_property
        dynamic: bool
        # Changed by the wiz_create_child_barn decorator
        wiz_outer_model_grain: Grain | None = None

        # Cob object
        cob: "Cob"
        autoid: int  # If the primakey is not provided, autoid will be used as primakey
        keyring: Any | tuple[Any]
        barns: list["Barn"]
        label_seed_map: dict[str, Seed]  # {label: Seed}
        seeds: tuple[Grain]  # @dual_property
        parent: "Cob" | None

        @classmethod
        def _set_up_class(klass, model: Type["Cob"]) -> None:
            klass.model = model
            klass._assign_grain_for_wiz_child_barn()
            # list() to avoid RuntimeError
            for name, value in list(model.__dict__.items()):
                if not isinstance(value, Grain):
                    continue
                klass._set_up_grain(value, name)
            klass.dynamic = False if klass.label_grain_map else True

        @classmethod
        def _assign_grain_for_wiz_child_barn(klass) -> None:
            # list() to avoid RuntimeError
            for value in list(klass.model.__dict__.values()):
                # issubclass() was not used because importing Cob would create a circular import
                if not hasattr(value, "__dna__"):
                    continue
                child_model = value  # Just to clarify
                # wiz_create_child_barn decorator previously had changed this attribute
                outer_model_grain = child_model.__dna__.wiz_outer_model_grain
                if not outer_model_grain:  # Assign to the model?
                    continue
                setattr(klass.model, outer_model_grain.label, outer_model_grain)
                annotations = get_type_hints(klass.model)
                annotations[outer_model_grain.label] = outer_model_grain.type
                klass.model.__annotations__ = annotations

        @dual_method
        def _set_up_grain(dna, grain: Grain, label: str) -> None:
            type_ = Any
            if label in dna.model.__annotations__:
                type_ = dna.model.__annotations__[label]
            grain._set_model_attrs(
                model=dna.model, label=label, type=type_)
            dna.label_grain_map[label] = grain

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
            return (len(dna.primakey_labels) > 0)

        @dual_property
        def is_compos_primakey(dna) -> bool:
            return (len(dna.primakey_labels) > 1)

        @dual_property
        def primakey_len(dna) -> int:
            return (len(dna.primakey_labels) or 1)

        @classmethod
        def create_barn(klass) -> "Barn":
            """Create a new Barn for the model.

            Returns:
                A new Barn object for the model.
            """
            # Lazy import to avoid circular imports
            from .barn import Barn
            return Barn(model=klass.model)

        def __init__(self, cob: "Cob"):
            self.cob = cob
            self.barns = []
            self.autoid = id(cob)  # Default autoid is the id of the cob object
            self.parent = None
            if self.dynamic:
                # Since the model is dynamic, the object-level grain map...
                # has to be different from the class-level
                self.label_grain_map = {}
            self.label_seed_map = {}
            for grain in self.grains:
                seed = Seed(cob, grain)
                self.label_seed_map[seed.label] = seed

        @property
        def seeds(self) -> tuple[Seed]:
            """Return a tuple of the cob's seeds."""
            return tuple(self.label_seed_map.values())

        @property
        def primakey_seeds(self) -> tuple[Seed]:
            """Return a tuple of the cob's primakey seeds."""
            return tuple(self.label_seed_map[label] for label in self.primakey_labels)

        def get_seed(self, label: str, default: Any = sentinel) -> Seed:
            """Return the seed for the given label.
            If the label does not exist, return the default value if provided,
            otherwise raise a KeyError."""
            if default is sentinel:
                return self.label_seed_map[label]
            return self.label_seed_map.get(label, default)

        def _create_dynamic_grain(self, label: str) -> Grain:
            """Add a dynamic grain to the Meta object.

            Args:
                label: The label of the dynamic grain to add

            This method is private solely to hide it from the user,
            but it will be called by the cob when a dynamic grain is created.
            """
            grain = Grain()
            self._set_up_grain(grain, label)
            seed = Seed(self.cob, grain)
            self.label_seed_map[label] = seed
            return grain

        def add_new_grain(self, label: str, value: Any) -> None:
            """Add a dynamic grain to the cob object.

            Args:
                label: The label of the dynamic grain to add
                value: The value of the dynamic grain to add

            Raises:
                ConsistencyError: If the cob model is not dynamic or if the grain already exists.
            """
            if not self.dynamic:
                raise ConsistencyError(fo(f"""
                    Cannot assign '{label}={value}' because the grain
                    has not been defined in the model.
                    Since at least one static grain has been defined in
                    the Cob-model, dynamic grain assignment is not allowed."""))
            if label in self.label_grain_map:
                raise ConsistencyError(fo(f"""
                    Cannot assign '{label}={value}' because the grain
                    has already been defined in the model."""))
            self._create_dynamic_grain(label)
            setattr(self.cob, label, value)

        def _add_barn(self, barn: "Barn") -> None:
            if barn in self.barns:
                raise RuntimeError(
                    "Barn object has already been added to the cob '{self.cob}'.")
            self.barns.append(barn)

        def _remove_barn(self, barn: "Barn") -> None:
            for index, item in enumerate(self.barns):
                if item is barn:
                    del self.barns[index]
                    return
            raise RuntimeError(
                "Barn object was not found in the '{self.cob}' cob.")

        @property
        def keyring(self) -> Any | tuple[Any]:
            """The keyring is either a primakey value (single primakey) or
            a tuple of primakey values (composite primakey).
            If the primakey is not defined, `autoid` is returned instead.

            Returns:
                tuple[Any] or Any: The keyring of the cob
            """
            if not self.primakey_defined:
                return self.autoid
            primakeys = tuple(seed.value for seed in self.primakey_seeds)
            if not self.is_compos_primakey:
                return primakeys[0]
            return primakeys

        def to_dict(self) -> dict[str, Any]:
            """Create a dictionary out of the cob.

            Every sub-Barn is converted into a list of cobs,
            which are then converted to dictionaries recursively.
            Every sub-cob is converted to a dictionary too.
            If key_name is set for a grain, it is used as the key instead of the label.

            Returns:
                A dictionary representation of the cob
            """
            # Lazy import to avoid circular imports
            from .barn import Barn
            from .cob import Cob
            key_value_map = {}
            for seed in self.seeds:
                key_name = seed.key_name or seed.label
                # If value is a barn or a cob, recursively process its cobs
                if isinstance(seed.value, Barn):
                    barn = seed.value
                    cobs = [cob.__dna__.to_dict() for cob in barn]
                    key_value_map[key_name] = cobs
                elif isinstance(seed.value, Cob):
                    cob = seed.value
                    key_value_map[key_name] = cob.__dna__.to_dict()
                else:
                    key_value_map[key_name] = seed.value
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

        def _check_constrains(self, seed: Seed, value: Any) -> None:
            """Checks the value against the grain constraints before setting it.

            Args:
                seed (Seed): The seed to check against.
                label (str): The grain label.
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
                raise ConsistencyError(f"Cannot assign '{seed.label}={value}' because the grain "
                                               "was defined as 'required=True'.")
            if seed.auto and (seed.was_set or (not seed.was_set and value is not None)):
                raise ConsistencyError(f"Cannot assign '{seed.label}={value}' because the grain "
                                               "was defined as 'auto=True'.")
            if seed.frozen and seed.was_set:
                raise ConsistencyError(f"Cannot assign '{seed.label}={value}' because the grain "
                                               "was defined as 'frozen=True'.")
            if seed.pk and self.barns:
                raise ConsistencyError(f"Cannot assign '{seed.label}={value}' because the grain "
                                               "was defined as 'pk=True' and the cob has been added to a barn.")
            if seed.unique and self.barns:
                for barn in self.barns:
                    barn._check_uniqueness_by_label(seed.label, value)

        def _check_and_remove_parent(self, seed: Seed, old_value: Any) -> None:
            """If the grain was previously set and the value is changing,
            remove parent links if any."""
            if not seed.was_set or seed.value is old_value:
                return
            # Lazy import to avoid circular imports
            from .barn import Barn
            from .cob import Cob
            if isinstance(seed.value, Barn):
                child_barn = seed.value
                child_barn._remove_parent_cob()  # Remove the parent for the barn
            elif isinstance(seed.value, Cob):
                child_cob = seed.value
                child_cob.__dna__.parent = None

        def _check_and_set_parent(self, seed: Seed):
            # Lazy import to avoid circular imports
            from .barn import Barn
            from .cob import Cob
            if isinstance(seed.value, Barn):
                child_barn = seed.value
                child_barn._set_parent_cob(self.cob)
            elif isinstance(seed.value, Cob):
                child_cob = seed.value
                child_cob.__dna__.parent = self.cob

        def _check_and_get_comparable_seeds(self, value: Any) -> list[Seed]:
            if not isinstance(value, self.model):
                raise ComparisonNotSupportedError(fo(f"""
                    Cannot compare this Cob '{self.model.__name__}' with
                    '{type(value).__name__}', because they are different types."""))
            comparables = [seed for seed in self.seeds if seed.comparable]
            if not comparables:
                raise ComparisonNotSupportedError(fo(f"""
                    Cannot compare Cob '{self.model.__name__}' objects because
                    none of its grains are marked as comparable.
                    To enable comparison, set comparable=True on at least one grain."""))
            return comparables

    Dna._set_up_class(model)
    return Dna
