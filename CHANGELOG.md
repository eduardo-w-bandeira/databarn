CHANGELOG
=========

All notable changes to this project will be documented in this file.

# Fixed
- `Dna.get_grain(label, default=...)` now returns the provided default when the label does not exist, instead of raising `KeyError`.
- `Barn.remove(cob)` now removes membership against the internally stored Cob for that keyring, preventing inconsistent state when a different equal-key instance is passed.
- `Barn.find(...)` and `Barn.find_all(...)` now treat deleted/missing attributes as non-matches instead of bubbling `AttributeError`.

# 1.8.0

# Breaking Changes
- `Grain(...)` no longer returns an instance. It is now a class factory function that generates a new Grain class (a subclass of `BaseGrain`) configured with the provided options.
- `Grist` objects are now instances of the generated Grain class, created per Cob instance.
- Removed `BaseGrain.force_set_value` to strengthen data integrity guarantees.
- Removed `BaseGrain.get_value_or_none`; use `BaseGrain.get_value(default=None)` instead.