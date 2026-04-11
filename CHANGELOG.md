CHANGELOG
=========

All notable changes to this project will be documented in this file.

# 1.8.0

## Breaking Changes

- `Grain(...)` no longer returns an instance. It is now a class factory function that generates a new Grain class (a subclass of `BaseGrain`) configured with the provided options.
- `Grist` objects are now instances of the generated Grain class, created per Cob instance.
