CHANGELOG
=========

All notable changes to this project will be documented in this file.

# 1.10.1

## Changed
- Added `Cob.__len__()` so `len(cob)` reports the number of active grains currently set on the instance, including grains with `None` values.

## Fixed
- `Cob.__delattr__()` now rejects deletion of `unique=True` grains in the same way it already rejected `pk=True`, `frozen=True`, and `required=True` grains.
- `Cob.__init__()` now calls grain factories only after all provided positional and keyword values have been assigned.

# 1.10.0

## Changed
- Created the exception `ValidationError`.
- Added the `@before_assign` decorator for registering pre-assignment hooks.
- Added the `@after_assign` decorator for registering post-assignment validation hooks.

# 1.9.2

## Changed
- Expanded branch-coverage tests (including targeted synthetic cases) and annotated defensive-path tests to clarify when runtime guards (for example, beartype) make specific branches unreachable in normal usage.

# 1.9.1

## Fixed
- `Barn._matches_criteria(...)` now checks the stored grain directly, so missing or unset grains are treated as non-matches instead of relying on legacy attribute access.

## Changed
- Added a public `__version__` attribute to the package.

# 1.9.0

## Added
- Added `@post_init` decorator support for post-initialization hooks in Cob models. Removed `__post_init__` special method.

## Changed
- Fixed: `Catalog()` now checks identity instead of equality.
- Grain and Cob internals now use `ABSENT` sentinel values for unset state in place of the `"<UNSET>"` string.


# 1.8.1

## Changed
- Allowed `None` values in primary key Grains.
- Updated Barn key validation to allow `None` as a primary key.
- Improved type-hint handling in `BaseDna` by resolving string/quoted annotations against the model module before constraint checks.
- `Barn(...).get(...)` and `Barn(...).has_primakey(...)` with labeled primary keys now validate provided label names and reject missing or unexpected labels.

## Fixed
- `Dna.get_grain(label, default=...)` now returns the provided default when the label does not exist, instead of raising `KeyError`.
- `Barn.remove(cob)` now removes membership against the internally stored Cob for that keyring, preventing inconsistent state when a different equal-key instance is passed.
- `Barn.find(...)` and `Barn.find_all(...)` now treat deleted/missing attributes as non-matches instead of bubbling `AttributeError`.
- Assigning values to Grains typed with quoted forward references (for example `"Barn['Child']"`) now no longer leaks internal beartype resolution errors.
- Deleting a declared Grain attribute that was never set is now a safe no-op.
- `autoenum=True` Grain validation now safely rejects non-class/non-`int`-compatible annotations without raising internal `issubclass()` type errors.


## Breaking Changes
- `Grain(...)` no longer returns an instance. It is now a class factory function that generates a new Grain class (a subclass of `BaseGrain`) configured with the provided options.
- `Grist` objects are now instances of the generated Grain class, created per Cob instance.
- Removed `BaseGrain.force_set_value` to strengthen data integrity guarantees.
- Removed `BaseGrain.get_value_or_none`; use `BaseGrain.get_value(default=None)` instead.