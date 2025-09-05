from __future__ import annotations
from typing import Any, Type


class Grain:
    """Cob-Model Grain: Grain definition for the Cob-like class."""
    label: str # This will be set in the Cob-model dna
    default: Any
    pk: bool
    auto: bool
    frozen: bool
    none: bool
    unique: bool
    type: Any # This will be set in the Cob-model dna
    bound_model: Type # This will be set in the Cob-model dna
    wiz_child_model: "Cob" = None  # This will be set in the Cob-model dna

    # Cob-instance specific attributes
    bound_cob: "Cob" # This will be set in the cob-instance dna
    was_set: bool # This will be set in the cob-instance dna
    value: Any  # Get or set the value of the grain, only in the cob instance


    def __init__(self, default: Any = None, pk: bool = False,
                 auto: bool = False, none: bool = True,
                 frozen: bool = False, unique: bool = False, **custom_attrs):
        self.default = default
        self.pk = pk
        self.auto = auto
        self.frozen = frozen
        self.none = none
        self.unique = unique
        self.__dict__.update(custom_attrs)
    
    def _set_model_attrs(self, bound_model: Type, label: str, type: Any) -> None:
        self.bound_model = bound_model
        self.label = label
        self.type = type

    def _set_wiz_child_model(self, wiz_child_model: "Cob") -> None:
        """Sets the wiz_child_model attribute.

        This method is private solely to hide it from the user.
        """
        self.wiz_child_model = wiz_child_model

    def _set_cob_attrs(self, bound_cob: "Cob", was_set: bool) -> None:
        """This will be set in the cob-instance

        This method is private solely to hide it from the user.
        """
        self.bound_cob = bound_cob
        self.was_set = was_set

    @property
    def value(self) -> Any:
        """Gets the value of the grain at the given moment."""
        return getattr(self.bound_cob, self.label)

    @value.setter
    def value(self, value: Any) -> None:
        """Sets the value of the grain.

        Be careful when using this, because it will
        overwrite the value of the grain in the cob.
        """
        setattr(self.bound_cob, self.label, value)

    def __repr__(self) -> str:
        """Returns a string representation of the Grain.

        F.ex.:
            Grain(label='my_grain', type=int, default=0, pk=False, auto=False,
            frozen=False, none=True)"
        """
        items = [f"{k}={v!r}" for k, v in self.__dict__.items()]
        sep_items = ", ".join(items)
        return f"{type(self).__name__}({sep_items})"



# class InstGrain(Grain):
#     """Instance Grain: Grain definition for the cob instance."""
#     bound_cob: "Cob"
#     was_set: bool
#     value: Any  # Get or set the value of the grain

#     def __init__(self, orig_grain: Grain, bound_cob: "Cob", label: str, type: Any, was_set: bool):
#         super().__init__(default=orig_grain.default,
#                          pk=orig_grain.pk, auto=orig_grain.auto,
#                          none=orig_grain.none, frozen=orig_grain.frozen,
#                          unique=orig_grain.unique)
#         self._set_label(label)
#         self._set_type(type)
#         self.bound_cob = bound_cob
#         self.was_set = was_set

#     @property
#     def value(self) -> Any:
#         """Gets the value of the grain at the given moment."""
#         return getattr(self.bound_cob, self.label)

#     @value.setter
#     def value(self, value: Any) -> None:
#         """Sets the value of the grain.

#         Be careful when using this, because it will
#         overwrite the value of the grain in the cob.
#         """
#         setattr(self.bound_cob, self.label, value)
