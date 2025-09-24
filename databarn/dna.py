from __future__ import annotations
import copy
from .trails import fo
from .exceptions import ConsistencyError, GrainTypeMismatchError, CobComparibilityError
from .grain import Grain, Sprout
from typing import Any, Type, get_type_hints


class classproperty(property):
    """A decorator that behaves like @property but for classmethods.
    Usage:
        class MyClass:
            _value = 42

            @classproperty
            def value(cls):
                return cls._value
    """

    def __get__(self, ob, klass):
        return self.fget(klass)


class dual_property:
    def __init__(self, method=None):
        self.method = method

    def __get__(self, ob, owner):
        if ob is None:
            # Class access
            return self.method(owner)
        else:
            # Instance access
            return self.method(ob)


class dual_method:
    def __init__(self, method):
        self.method = method

    def __get__(self, ob, owner):
        def wrapper(*args, **kwargs):
            dna = owner if ob is None else ob
            return self.method(dna, *args, **kwargs)
        return wrapper


def create_dna(model: Type["Cob"]) -> "Dna":
    """
    """
    class Dna:

        # Model
        label_grain_map: dict[str, Grain]  # {label: Grain}
        primakey_labels: list[str]
        is_compos_primakey: bool
        primakey_defined: bool
        keyring_len: int
        dynamic: bool
        grains: tuple[Grain]  # @property
        # Changed by the wiz_create_child_barn decorator
        wiz_outer_model_grain: Grain | None = None
        parent: "Cob" | None = None

        # Cob object
        cob: "Cob"
        autoid: int  # If the primakey is not provided, autoid will be used as primakey
        keyring: Any | tuple[Any]
        barns: list["Barn"]
        label_sprout_map: dict[str, Sprout] # {label: Sprout}

        @classmethod
        def _set_up_class(klass, model: Type["Cob"]) -> None:
            klass.model = model
            klass.primakey_labels = []
            klass.label_grain_map = {}
            klass._assign_wiz_child_grain()
            # list() to avoid RuntimeError
            for name, value in list(model.__dict__.items()):
                if not isinstance(value, Grain):
                    continue
                klass._set_up_grain(klass, value, name)
            klass.dynamic = False if klass.label_grain_map else True
            klass.primakey_defined = len(klass.primakey_labels) > 0
            klass.is_compos_primakey = len(klass.primakey_labels) > 1
            klass.keyring_len = len(klass.primakey_labels) or 1

        # @staticmethod
        # def _is_dynamic(model: Type["Cob"]) -> bool:
        #     for value in model.__dict__.values():
        #         if isinstance(value, Grain):
        #             return False
        #         if hasattr(value, "__dna__") and value.__dna__.wiz_outer_model_grain:
        #             return False
        #     return True

        @classmethod
        def _assign_wiz_child_grain(klass) -> None:
            # list() to avoid RuntimeError
            for value in list(klass.model.__dict__.values()):
                # issubclass() was not used because importing Cob would create a circular import
                if not hasattr(value, "__dna__"):
                    continue
                child_model = value  # Just to clarify
                # wiz_create_child_barn decorator previously had changed this attribute
                outer_model_grain = child_model.__dna__.wiz_outer_model_grain
                if not outer_model_grain:  # Wiz assign to the model
                    continue
                setattr(klass.model, outer_model_grain.label, outer_model_grain)
                annotations = get_type_hints(klass.model)
                annotations[outer_model_grain.label] = outer_model_grain.type
                klass.model.__annotations__ = annotations

        @staticmethod
        def _set_up_grain(dna, grain: Grain, label: str) -> None:
            type_ = Any
            if label in dna.model.__annotations__:
                type_ = dna.model.__annotations__[label]
            grain._set_model_attrs(
                model=dna.model, label=label, type=type_)
            if grain.pk:
                dna.primakey_labels.append(grain.label)
            dna.label_grain_map[label] = grain

        @classmethod
        def create_barn(klass) -> "Barn":
            """Create a new Barn for the model.

            Returns:
                A new Barn object for the model.
            """
            # Lazy import to avoid circular imports
            from .barn import Barn
            return Barn(model=klass.model)

        @dual_property
        def grains(dna) -> tuple[Grain]:
            """Return a tuple of the grains of the model or cob."""
            return tuple(dna.label_grain_map.values())

        def __init__(self, cob: "Cob"):
            self.cob = cob
            self.barns = []
            self.autoid = id(cob)  # Default autoid is the id of the cob object
            self.parent = None
            if self.dynamic:
                self.label_grain_map = {}
                self.primakey_labels = []
            self.label_sprout_map = {}
            for grain in self.grains:
                sprout = Sprout(cob, grain)
                self.label_sprout_map[sprout.label] = sprout

        def get_sprout(self, label: str) -> Grain:
            """Returns the grain with the given label.
            Args:
                label: The label of the grain to return.
            Raises:
                KeyError: If the grain with the given label does not exist.
            Returns:
                The grain with the given label.
            """
            return self.label_grain_map[label]

        def _set_up_parent_if(self, grain: Grain):
            # Lazy import to avoid circular imports
            from .barn import Barn
            from .cob import Cob
            if isinstance(grain.value, Barn):
                child_barn = grain.value
                child_barn._set_parent_cob(self.cob)
            elif isinstance(grain.value, Cob):
                child_cob = grain.value
                child_cob.__dna__.parent = self.cob

        def _remove_parent_if(self, grain: Grain):
            # Lazy import to avoid circular imports
            from .barn import Barn
            from .cob import Cob
            if isinstance(grain.value, Barn):
                child_barn = grain.value
                child_barn._remove_parent_cob()  # Remove the parent for the barn
            elif isinstance(grain.value, Cob):
                child_cob = grain.value
                child_cob.__dna__.parent = None

        def _create_dynamic_grain(self, label: str) -> Grain:
            """Adds a dynamic grain to the Meta object.

            Args:
                label: The label of the dynamic grain to add

            This method is private solely to hide it from the user,
            but it will be called by the cob when a dynamic grain is created.
            """
            grain = Grain()
            self._set_up_grain(self, grain, label)

        @property
        def primakey_sprouts(dna) -> tuple[Grain]:
            """Returns a tuple of the model's primakeys grains."""
            return tuple(dna.label_grain_map[label] for label in dna.primakey_labels)

        def add_new_grain(self, label: str, value: Any) -> None:
            """Adds a dynamic grain to the cob object.

            Args:
                label: The label of the dynamic grain to add
                value: The value of the dynamic grain to add

            Raises:
                ConsistencyError: If the cob model is not dynamic or if the grain already exists.
            """
            if not self.dynamic:
                raise ConsistencyError(fo(f"""
                    Cannot assign '{label}={value}' because the grain
                    has not been defined in the Cob-model.
                    Since at least one static grain has been defined in
                    the Cob-model, dynamic grain assignment is not allowed."""))
            if label in self.label_grain_map:
                raise ConsistencyError(fo(f"""
                    Cannot assign '{label}={value}' because the grain
                    has already been defined in the Cob-model."""))
            self._create_dynamic_grain(label)
            sprout = Sprout(self.cob, self.label_grain_map[label])
            self.label_sprout_map[label] = sprout
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
            """Returns the keyring of the cob.

            The keyring is either a primakey or a tuple of primakeys. If the
            primakey-grain is not defined, the autoid is returned instead.

            Returns:
                tuple[Any] or Any: The keyring of the cob
            """
            if not self.primakey_defined:
                return self.autoid
            primakeys = tuple(grain.value for grain in self.primakey_sprouts)
            if not self.is_compos_primakey:
                return primakeys[0]
            return primakeys

        def to_dict(self) -> dict[str, Any]:
            """Returns a dictionary representation of the cob.

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
            for grain in self.grains:
                key_name = grain.key_name or grain.label
                # If value is a barn or a cob, recursively process its cobs
                if isinstance(grain.value, Barn):
                    barn = grain.value
                    cobs = [cob.__dna__.to_dict() for cob in barn]
                    key_value_map[key_name] = cobs
                elif isinstance(grain.value, Cob):
                    cob = grain.value
                    key_value_map[key_name] = cob.__dna__.to_dict()
                else:
                    key_value_map[key_name] = grain.value
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

        def _check_and_set_up(self, grain: Grain, label: str, value: Any) -> None:
            """Checks the value against the grain constraints before setting it.

            Args:
                grain (Grain): The grain to check against.
                label (str): The grain label.
                value (Any): The value to check and set.
            Returns:
                None
            """
            if grain.type is not Any and value is not None:
                import typeguard  # Lazy import to avoid unecessary computation
                try:
                    typeguard.check_type(value, grain.type)
                except typeguard.TypeCheckError:
                    raise GrainTypeMismatchError(fo(f"""
                        Cannot assign '{label}={value}' because the grain
                        was defined as {grain.type}, but got {type(value)}.
                        """)) from None
            if grain.required and value is None and not grain.auto:
                raise ConsistencyError(f"Cannot assign '{label}={value}' because the grain "
                                       "was defined as 'required=True'.")
            if grain.auto and (grain.was_set or (not grain.was_set and value is not None)):
                raise ConsistencyError(f"Cannot assign '{label}={value}' because the grain "
                                       "was defined as 'auto=True'.")
            if grain.frozen and grain.was_set:
                raise ConsistencyError(f"Cannot assign '{label}={value}' because the grain "
                                       "was defined as 'frozen=True'.")
            if grain.pk and self.barns:
                raise ConsistencyError(f"Cannot assign '{label}={value}' because the grain "
                                       "was defined as 'pk=True' and the cob has been added to a barn.")
            if grain.unique and self.barns:
                for barn in self.barns:
                    barn._check_uniqueness_by_label(grain.label, value)
            if grain.was_set and grain.value is not value:
                # If the grain was previously set and the value is changing, remove parent links if any
                self._remove_parent_if(grain)

        def _check_and_get_comparable_grains(self, value: Any) -> None:
            if not isinstance(value, self.model):
                raise CobComparibilityError(fo(f"""
                    Cannot compare this Cob '{self.model.__name__}' with
                    '{type(value).__name__}', because they are different types."""))
            comparable_grains = [
                grain for grain in self.grains if grain.comparable]
            if not comparable_grains:
                raise CobComparibilityError(fo(f"""
                    Cannot compare Cob '{self.model.__name__}' objects because
                    none of its grains are marked as comparable.
                    To enable comparison, set comparable=True on at least one grain."""))
            return comparable_grains

    Dna._set_up_class(model)
    return Dna
