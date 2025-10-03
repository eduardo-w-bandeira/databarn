from __future__ import annotations
from typing import Any, Iterator, Type
from .cob import Cob
from .grain import Seed
from .trails import fo
from .exceptions import BarnConsistencyError, DataBarnSyntaxError, ConstraintViolationError


class Barn:
    """In-memory storage for cob-like objects.

    Provides methods to find and retrieve
    Cob objects based on their primakeys or seeds.
    """
    model: Type[Cob]
    _next_auto_enum: int
    _keyring_cob_map: dict
    parent_cob: Cob | None = None

    def __init__(self, model: Type[Cob] = Cob):
        """Initialize the Barn.

        Args:
            model: The Cob-like class whose objects will be stored in this Barn.
        """
        # issubclass also returns True if the subclass is the parent class
        if not issubclass(model, Cob):
            raise BarnConsistencyError(
                f"Expected a Cob-like class for the model arg, but got {model}.")
        self.model = model
        self._next_auto_enum = 1
        self._keyring_cob_map: dict = {}

    def _assign_auto(self, cob: Cob, value: int) -> None:
        """Assign an auto seed value to the cob, if applicable.

        Args:
            cob: The cob whose auto seeds should be assigned.
            value: The value to assign to the auto seeds.
        """
        for seed in cob.__dna__.seeds:
            if seed.auto and seed.get_value() is None:
                # Bypass __setattr__ to avoid triggering any custom logic
                seed.force_set_value(value)

    def _check_keyring(self, keyring: Any | tuple) -> bool:
        """Check if the primakey(s) is unique and not None.

        Args:
            keyring: The primakey or tuple of composite primakeys.

        Returns:
            True if the keyring is valid.

        Raises:
            BarnConsistencyError: If the keyring is None or already in use.
        """
        if self.model.__dna__.is_compos_primakey:
            has_none = any(primakey is None for primakey in keyring)
            if has_none:
                raise BarnConsistencyError("None is not valid as primakey.")
        elif keyring is None:
            raise BarnConsistencyError("None is not valid as primakey.")
        if keyring in self._keyring_cob_map:
            raise BarnConsistencyError(
                f"Primakey {keyring} already in use.")
        return True

    def _check_uniqueness_for(self, seeds: list) -> bool:
        """Check uniqueness of the unique-type seeds against barn cobs.

        Args:
            unique_type_seeds: The list of unique-type seeds to check.

        Returns:
            True if the seed is unique.

        Raises:
            BarnConsistencyError: If the value is already in use for that particular seed.
                None value is allowed.
        """

        return True

    def _check_uniqueness_by_cob(self, cob: Cob) -> bool:
        """Check uniqueness of the unique-type seeds against the stored cobs.

        Args:
            cob: The cob whose unique seeds should be checked.

        Returns:
            True if the seed is unique.

        Raises:
            BarnConsistencyError: If the value is already in use for that particular seed.
                None value is allowed.
        """
        uniques: list = []
        for seed in cob.__dna__.seeds:
            if seed.unique:
                uniques.append(seed)
        if not uniques:  # Prevent unnecessary processing
            return True
        for cob in self:
            for seed in uniques:
                if seed.get_value() == getattr(cob, seed.label):
                    raise ConstraintViolationError(fo(f"""
                        The value {seed.get_value()} for the unique grain
                        '{seed.label}' is already in use by {cob}."""))
        return True

    def _check_uniqueness_by_value(self, seed: Seed, value: Any) -> bool:
        for cob in self:
            if value == getattr(cob, seed.label):
                raise ConstraintViolationError(fo(f"""
                    The value {value} for the unique grain
                    '{seed.label}' is already in use by {cob}."""))
        return True

    def add(self, cob: Cob) -> Barn:
        """Add a cob to the Barn in order.

        Args:
            cob: The cob-like object to add. The cob must be
                of the same type as the model defined for this Barn.

        Raises:
            BarnConsistencyError: If the cob is not of the same type as the model
                defined for this Barn.
            BarnConsistencyError: If the primakey is in use or is None.
            BarnConsistencyError: If a unique seed is not unique.

        Returns:
            Barn: The current Barn object, to allow method chaining.
        """
        if not isinstance(cob, self.model):
            raise BarnConsistencyError(fo(f"""
                Cannot add {cob} to the barn because it is not of the same type
                as the model defined for this Barn ({self.model})."""))
        if cob.__dna__.parent:
            raise BarnConsistencyError(
                f"Cannot add {cob} to the barn because it already has a parent cob.")
        self._assign_auto(cob, self._next_auto_enum)
        self._next_auto_enum += 1
        cob.__dna__._add_barn(self)
        self._check_keyring(cob.__dna__.keyring)
        self._check_uniqueness_by_cob(cob)
        self._keyring_cob_map[cob.__dna__.keyring] = cob
        cob.__dna__.parent = self.parent_cob
        return self

    def add_all(self, *cobs: Cob) -> Barn:
        """Append multiple cobs to the Barn.

        Args:
            *cobs: The cob-like objects to add. Each cob must be
                of the same type as the model defined for this Barn.

        Returns:
            Barn: The current Barn object, to allow method chaining.
        """
        for cob in cobs:
            self.add(cob)
        return self

    def append(self, cob: Cob) -> None:
        """Similarly to add(), append a cob to the Barn, but return None."""
        self.add(cob)
        return None

    def _get_keyring(self, *primakeys, **labeled_primakeys) -> tuple[Any] | Any:
        """Return a keyring as a tuple of primakeys or a single primakey.

        You can provide either positional args or kwargs, but not both.

        Raises:
            BarnSyntaxError: If nothing was provided, or
                both positional primakeys and labeled_keys were provided, or
                the number of primakeys does not match the primakey seeds.
        """

        if not primakeys and not labeled_primakeys:
            raise DataBarnSyntaxError(
                "No primakeys or labeled_primakeys were provided.")
        if primakeys and labeled_primakeys:
            raise DataBarnSyntaxError("Both positional primakeys and labeled_primakeys "
                                  "cannot be provided together.")
        if primakeys:
            if self.model.__dna__.primakey_len != (primakeys_len := len(primakeys)):
                raise DataBarnSyntaxError(f"Expected {self.model.__dna__.primakey_len} primakeys, "
                                      f"but got {primakeys_len}.")
            keyring = primakeys[0] if primakeys_len == 1 else primakeys
        else:
            if self.model.__dna__.dynamic:
                raise DataBarnSyntaxError(
                    "To use labeled_keys, the provided model for "
                    f"{self.__name__} cannot be dynamic.")
            if self.model.__dna__.primakey_len != len(labeled_primakeys):
                raise DataBarnSyntaxError(f"Expected {self.model.__dna__.primakey_len} labeled_keys, "
                                      f"got {len(labeled_primakeys)} instead.")
            primakey_lst = [labeled_primakeys[seed.label]
                            for seed in self.model.__dna__.primakey_seeds]
            keyring = tuple(primakey_lst)
        return keyring

    def get(self, *primakeys, **labeled_primakeys) -> Cob | None:
        """Return a cob from the Barn, given its primakey or labeled_keys.

        Raises:
            BarnSyntaxError: If nothing was provided, or
                both positional primakeys and labeled_primakeys were provided, or
                the number of primakeys does not match the primakey seeds.

        Returns:
            The cob associated with the primakey(s), or None if not found.
        """
        keyring = self._get_keyring(*primakeys, **labeled_primakeys)
        return self._keyring_cob_map.get(keyring, None)

    def remove(self, cob: Cob) -> None:
        """Remove a cob from the Barn.

        Args:
            cob: The cob to remove
        """
        del self._keyring_cob_map[cob.__dna__.keyring]
        cob.__dna__._remove_barn(self)

    def _matches_criteria(self, cob: Cob, **labeled_values) -> bool:
        """Check if a cob matches the given criteria.

        Args:
            cob: The cob to check
            **labeled_values: The criteria to match

        Returns:
            bool: True if the cob matches the criteria, False otherwise
        """
        for label, value in labeled_values.items():
            # If dynamic, the cob may not have the attribute
            # If the cob doesn't have the attribute, it doesn't match
            if self.model.__dna__.dynamic and not hasattr(cob, label):
                return False
            if getattr(cob, label) != value:
                return False
        return True

    def find_all(self, **labeled_values) -> Barn:
        """Find all cobs in the Barn that match the given criteria.

        Args:
            **labeled_values: The criteria to match

        Returns:
            Barn: A Barn containing all cobs that match the criteria
        """
        results = Barn(self.model)
        for cob in self._keyring_cob_map.values():
            if self._matches_criteria(cob, **labeled_values):
                results.add(cob)
        return results

    def find(self, **labeled_values) -> Cob:
        """Find the first cob in the Barn that matches the given criteria.

        Args:
            **labeled_values: seed_label=value used as the criteria to match

        Returns:
            Cob: The first cob that matches the criteria, or None not found.
        """
        for cob in self._keyring_cob_map.values():
            if self._matches_criteria(cob, **labeled_values):
                return cob
        return None

    def has_primakey(self, *primakeys, **labeled_primakeys) -> bool:
        """Check if the provided primakey(s) is(are) in the Barn."""
        keyring = self._get_keyring(*primakeys, **labeled_primakeys)
        return keyring in self._keyring_cob_map

    def __len__(self) -> int:
        """Return the number of cobs in the Barn.

        Returns:
            int: The number of cobs in the Barn.
        """
        return len(self._keyring_cob_map)

    def __repr__(self) -> str:
        length = len(self)
        word = "cob" if length == 1 else "cobs"
        return f"{self.__class__.__name__}({length} {word})"

    def __contains__(self, cob: Cob) -> bool:
        """Check if a cob is in the Barn.

        Args:
            cob: Cob to check for membership

        Returns:
            bool: True if the cob is in the Barn, False otherwise
        """
        return cob in self._keyring_cob_map.values()

    def __getitem__(self, index: int | slice) -> Cob | Barn:
        """Get a cob or a slice of cobs from the Barn.

        Args:
            index: int or slice of the cob(s) to retrieve

        Returns:
            cob or barn: The retrieved cob(s)

        Raises:
            IndexError: If the index is not valid
        """
        cob_or_cobs = list(self._keyring_cob_map.values())[index]
        if type(index) is int:
            return cob_or_cobs
        elif type(index) is slice:
            results = Barn(self.model)
            [results.add(cob) for cob in cob_or_cobs]
            return results
        raise IndexError("Invalid index")

    def __iter__(self) -> Iterator[Cob]:
        """Iterate over the cobs in the Barn.

        Ex.: `for cob in barn: print(cob)`

        Yields:
            Cob: Each cob in the Barn, in the order they were added.
        """
        for cob in self._keyring_cob_map.values():
            yield cob

    def _set_parent_cob(self, parent_cob: Cob) -> None:
        """Set the parent cob for this barn and its child cobs."""
        if self.parent_cob:
            raise BarnConsistencyError(fo(f"""
                This barn already has {self.parent_cob} as parent cob.
                A barn can only have one parent cob."""))
        self.parent_cob = parent_cob
        for cob in self:
            cob.__dna__.parent = parent_cob

    def _remove_parent_cob(self) -> None:
        """Remove the parent cob for this barn and its child cobs."""
        if not self.parent_cob:
            return
        self.parent_cob = None
        for cob in self:
            cob.__dna__.parent = None
