from __future__ import annotations
from collections.abc import Iterator
from typing import Any, Generic
from beartype import beartype

from .constants import ABSENT
from .types import Cob, CobT
from .grain import Grist
from .trails import fo, Catalog
from .exceptions import BarnConstraintViolationError, DataBarnSyntaxError, CobConstraintViolationError


@beartype
class Barn(Generic[CobT]):
    """In-memory storage for cob-like objects.

    Provides methods to find and retrieve
    Cob objects based on their primakeys or grists.
    """
    model: type[CobT]
    _next_autoenum: int
    _keyring_cob_map: dict
    parent_cobs: Catalog

    def __init__(self, model: type[CobT] = Cob):
        """Initialize the Barn.

        Args:
            model: The Cob-like class whose objects will be stored in this Barn.
        """
        # issubclass also returns True if the subclass is the parent class
        # if not issubclass(model, Cob):
        #     raise BarnConstraintViolationError(
        #         f"Expected a Cob-like class for the model arg, but got {model}.")
        self.model = model
        self._next_autoenum = 1
        self._keyring_cob_map: dict = {}
        self.parent_cobs = Catalog()

    def _assign_autoenum_if(self, cob: CobT) -> None:
        """Assign an autoenum grist value to the cob, if applicable.

        Args:
            cob: The cob whose autoenum grists should be assigned.
        """
        used_autoenum: bool = False
        for grist in cob.__dna__.grists:
            if grist.autoenum and not grist.attr_exists():
                grist.set_value(self._next_autoenum)
                used_autoenum = True
        if used_autoenum:
            self._next_autoenum += 1

    def _validate_keyring(self, cob: CobT) -> None:
        keyring = cob.__dna__.get_keyring()
        if keyring is ABSENT:
            raise BarnConstraintViolationError(f"Primakey(s) was not assigned for {cob}.")
        if keyring is None or (cob.__dna__.is_compos_primakey and None in keyring):
            raise BarnConstraintViolationError(f"None is not valid as primakey for {cob}.")
        if keyring in self._keyring_cob_map:
            raise BarnConstraintViolationError(
                f"Primakey {keyring} already in use for {cob}.")

    def _check_uniqueness_by_cob(self, cob: CobT) -> bool:
        """Check uniqueness of the unique-type grists against the stored cobs.

        Args:
            cob: The cob whose unique grists should be checked.

        Returns:
            True if the grist is unique.

        Raises:
            BarnConstraintViolationError: If the value is already in use for that particular grist.
                None value is allowed.
        """
        uniques: list = []
        for grist in cob.__dna__.grists:
            if grist.unique:
                uniques.append(grist)
        if not uniques:  # Prevent unnecessary processing
            return True
        for cob in self:
            for grist in uniques:
                if grist.get_value() == getattr(cob, grist.label):
                    raise CobConstraintViolationError(fo(f"""
                        The value {grist.get_value()} for the unique grain
                        '{grist.label}' is already in use by {cob}."""))
        return True

    def _check_uniqueness_by_value(self, grist: Grist, value: Any) -> bool:
        for cob in self:
            if value == getattr(cob, grist.label):
                raise CobConstraintViolationError(fo(f"""
                    The value {value} for the unique grain
                    '{grist.label}' is already in use by {cob}."""))
        return True

    def add(self, cob: CobT) -> Barn[CobT]:
        """Add a cob to the Barn in order.

        Args:
            cob: The cob-like object to add. The cob must be
                of the same type as the model defined for this Barn.

        Raises:
            BarnConstraintViolationError: If the cob is not of the same type as the model
                defined for this Barn.
            BarnConstraintViolationError: If the primakey is in use or is None.
            BarnConstraintViolationError: If a unique grist is not unique.

        Returns:
            Barn: The current Barn object, to allow method chaining.
        """
        if not isinstance(cob, self.model):
            raise BarnConstraintViolationError(fo(f"""
                Cannot add {cob} to the barn because it is not of the same type
                as the model defined for this Barn ({self.model})."""))
        self._assign_autoenum_if(cob)
        self._validate_keyring(cob)
        self._check_uniqueness_by_cob(cob)
        self._keyring_cob_map[cob.__dna__.get_keyring()] = cob
        cob.__dna__._add_barn(self)
        for parent_cob in self.parent_cobs:
            cob.__dna__._add_parent(parent_cob)
        return self

    def add_all(self, *cobs: CobT) -> Barn[CobT]:
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

    def append(self, cob: CobT) -> None:
        """Similarly to add(), append a cob to the Barn, but return None."""
        self.add(cob)
        return None  # For explicitness

    def _get_keyring(self, *primakeys, **labeled_primakeys) -> tuple[Any, ...] | Any:
        """Return a keyring as a tuple of primakeys or a single primakey.

        You can provide either positional args or kwargs, but not both.

        Raises:
            BarnSyntaxError: If nothing was provided, or
                both positional primakeys and labeled_keys were provided, or
                the number of primakeys does not match the primakey grists.
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
                    f"{self.__class__.__name__} cannot be dynamic.")
            if self.model.__dna__.primakey_len != len(labeled_primakeys):
                raise DataBarnSyntaxError(f"Expected {self.model.__dna__.primakey_len} labeled_keys, "
                                          f"got {len(labeled_primakeys)} instead.")
            primakey_lst = [labeled_primakeys[label]
                            for label in self.model.__dna__.primakey_labels]
            if not self.model.__dna__.is_compos_primakey:
                keyring = primakey_lst[0]
            else:
                keyring = tuple(primakey_lst)
        return keyring

    def get(self, *primakeys, **labeled_primakeys) -> CobT | None:
        """Return a cob from the Barn, given its primakey or labeled_keys.

        Raises:
            BarnSyntaxError: If nothing was provided, or
                both positional primakeys and labeled_primakeys were provided, or
                the number of primakeys does not match the primakey grists.

        Returns:
            The cob associated with the primakey(s), or None if not found.
        """
        keyring = self._get_keyring(*primakeys, **labeled_primakeys)
        return self._keyring_cob_map.get(keyring, None)

    def remove(self, cob: CobT) -> None:
        """Remove a cob from the Barn.

        Args:
            cob: The cob to remove
        """
        del self._keyring_cob_map[cob.__dna__.get_keyring()]
        cob.__dna__._remove_barn(self)

    def _matches_criteria(self, cob: CobT, **labeled_values) -> bool:
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

    def find_all(self, **labeled_values) -> Barn[CobT]:
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

    def find(self, **labeled_values) -> CobT | None:
        """Find the first cob in the Barn that matches the given criteria.

        Args:
            **labeled_values: grist_label=value used as the criteria to match

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

    def _add_parent_cob(self, parent_cob: Cob) -> None:
        """Set the parent cob for this barn and its child cobs."""
        self.parent_cobs.add(parent_cob)
        for cob in self:
            cob.__dna__._add_parent(parent_cob)

    def _remove_parent_cob(self, parent_cob: Cob) -> None:
        """Remove the parent cob for this barn and its child cobs."""
        self.parent_cobs.remove(parent_cob)
        for cob in self:
            cob.__dna__._remove_parent(parent_cob)
