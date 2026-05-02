DataBarn: Comprehensive Project Overview
========================================

# What is DataBarn?
**DataBarn** is a lightweight, typed, in-memory Object-Relational Mapping (ORM) library for Python. It merges the strictness of traditional database schemas with the ergonomics of Python dictionaries, enabling both dot-notation field access and dictionary-style operations.

The official package description is: *"Dictionary with Dot Notation • Schema definitions • Type validation • Lightweight in-memory ORM"*

DataBarn helps you:

- Define strongly-typed, schema-driven data models using standard Python classes
- Validate values at runtime against type annotations (via `beartype`) and custom constraints
- Store instances in ordered collections (`Barn`) that enforce primary key uniqueness and field uniqueness
- Represent hierarchical/nested data using one-to-one and one-to-many relationships
- Convert unstructured data (dict/JSON) into validated schema objects while preserving original keys

# Mental Model
If you think in "database-ish" terms:

| DataBarn | Database Analogy |
|----------|------------------|
| `Cob` | Row/Record/Object |
| `Grain` (class-level) | Column schema declaration |
| `Grain` (instance-level) | Column value binding in a specific row |
| `Barn` | Table/Collection with key index |
| `__dna__` | Schema metadata + validation + runtime engine |
| `Decorators` (`@one_to_many_grain`, `@one_to_one_grain`) | Foreign key relationships |

## Other Conventions
- `label` = Grain attribute name in the Cob-model
- `symbol` = any attribute name other than the label
- `key` = Grain name used in the dict/JSON output
- `primakey` = primary key value
- `keyring` = a single `primakey` or a tuple of composite `primakey`s

# Core Abstractions

DataBarn revolves around four central concepts:

## 1. **Cob** (The Model Instance)

A `Cob` represents a single data entity/record. You define models by subclassing `Cob` and declaring fields via type annotations and `Grain` configurations.

Key behaviors:
- **Dot-notation access**: `cob.field_name` or dictionary-style `cob["field_name"]`
- **Metaclass-managed schema**: a custom metaclass (`MetaCob`) registers defined fields at class creation time
- **Validation on assignment**: runtime type checking via `beartype` when setting field values
- **Collection length**: `len(cob)` returns the number of active grains currently set on the instance; grains assigned `None` still count, while deleted grains do not
- **Post-initialization hooks**: decorate a method with `@post_init` to run custom logic after all grains are assigned/defaulted during initialization
- **Before-assignment hooks**: decorate a method with `@treat_before_assign('<label>')` to preprocess or validate values before they are assigned to a grain. The user is encouraged to raise `ValidationError` from those hooks to indicate validation failures.
- **Post-assignment hooks**: decorate a method with `@post_assign('<label>')` to validate the assigned value after it has been set. The hook cannot modify the value—it can only raise `ValidationError` to reject the assignment. Prefer `ValidationError` for validation failures so callers can handle them consistently.
- **Constraint enforcement**: covers initialization, attribute assignment, and deletion
- **Mapping-like helpers**: `cob.get(label)`, `cob.update(dict)`, `cob.pop(label)`, and iteration via `cob.items()`, `cob.keys()`, `cob.values()`
- **Comparison operators**: `==`, `!=`, `<`, `<=`, `>`, `>=` (based only on fields marked `comparable=True`)
- **Reserved attribute**: `__dna__` stores internal metadata and cannot be deleted or reassigned

**Post-Initialization Hook Example:**

Use the `@post_init` decorator on a method to execute custom logic after initialization:

```python
class User(Cob):
    email: str = Grain(required=True)
    
    @post_init
    def validate_email(self):
        if "@" not in self.email:
            raise ValueError("Invalid email format")

```

## Before-Assign Hook Example:

Use `@treat_before_assign` to register a pre-assignment hook for a specific label. The hook may transform the incoming value or raise `ValidationError` to reject it; prefer `ValidationError` for validation failures so callers can handle them consistently.

```python
class User(Cob):
    name: str = Grain(required=True)

    @treat_before_assign('name')
    def _prepare_name(self, value):
        if not isinstance(value, str) or not value.strip():
            raise ValidationError("name must be a non-empty string")
        return value.strip().title()
```

**After-Assign Hook Example:**

Use `@post_assign` to register a post-assignment hook for a specific label. The hook validates the value after assignment and may raise `ValidationError` to reject invalid assignments; prefer `ValidationError` for consistency.

```python
class Account(Cob):
    email: str = Grain(required=True)

    @post_assign('email')
    def _validate_email(self):
        if '@' not in self.email:
            raise ValidationError("Email must contain '@' symbol")
```

## 2. **Grain** (The Schema Field Declaration)

`Grain(...)` is a factory function that returns a generated Grain class for a field (a subclass of `BaseGrain`).
That generated class stores schema-level metadata and constraints for the field.

Common grain options:
- **`required`**: field must be provided during initialization (unless a default/factory exists)
- **`pk`**: marks the field as part of the primary key; `None` is a valid primary-key value, including in composite keys
- **`autoenum`**: primary key is auto-assigned (typically integer) when the cob is added to a `Barn`
- **`unique`**: value must be unique across all cobs in the same `Barn` (including `None` values)
- **`frozen`**: once set, the value cannot be reassigned
- **`comparable`**: enables the field in comparison operations (`<`, `>`, etc.)
- **`factory`**: a callable that generates an initial value (commonly used for relationship fields and collections)
- **`key`**: the serialized name used in `to_dict()` / `to_json()` output (preserves original dict keys)
- **Type annotation**: the Python type declared in the class determines validation rules via `beartype`

## 3. **Grain** (The Instance-Level Field Binding)

While a generated Grain class defines class-level schema metadata, a Grain is also the runtime instance created from that generated class and bound to a specific `Cob`.

A Grain instance encapsulates:
- The field label and owning `Cob`
- Current runtime state (whether the attribute is set, deleted, or unset)
- Getter/setter behavior ensuring validation rules hold
- Methods: `get_value()`, `set_value()`, `attr_exists()` (to check if currently active)

## 4. **Barn** (The Ordered Collection)

A `Barn` is an ordered, model-aware container that stores `Cob` objects of a single type. It acts like a database table with constraint enforcement.

Key features:
- **Type enforcement**: only accepts instances of its configured model type
- **Primary key uniqueness**: validates that the primary key exists (auto-assigned if `autoenum=True`) and is unique; `None` is accepted as a primary-key value, including in composite keys
- **Unique-field enforcement**: fields marked `unique=True` cannot repeat across stored cobs
- **Lookups**:
  - `barn.get(key)` — retrieves by primary key (positional for static models, keyword for either)
  - `barn.has_primakey(key)` — checks if primary key exists
  - `barn.find(**kwargs)` / `barn.find_all(**kwargs)` — attribute-based filtering (only matches active field values)
- **Collection protocol**: supports `len()`, iteration, slicing (returns new `Barn`), and membership testing (`cob in barn`)
- **Operations**: `add()`, `add_all()`, `append()`, `remove()`

## 5. **BaseDna** (The Internal Metadata Engine)

To avoid namespace pollution, DataBarn keeps internal state in a `Dna` instance accessible via `.__dna__`, splitting responsibilities into:

- **Class-level metadata**: the established schema and grain definitions
- **Instance-level metadata**: active field values, deleted/unset flags, parent relationships, and barn associations

The DNA also provides:
- Dictionary-like utilities: `items()`, `keys()`, `values()`, `get()`, `pop()`, `popitem()`, `setdefault()`, `update()`, `clear()`
- Serialization methods: `to_dict()` and `to_json()`
- Constraint validation and parent/barn bookkeeping


# Static vs. Dynamic Models

The model mode is determined by class annotations and affects behavior throughout the system:

## Static Models
- Declared when a `Cob` subclass has **at least one annotated field**
-- **Reject unknown fields** at initialization or assignment (raise `SchemeViolationError`)
- Support **positional arguments** in initialization (by field order)
- Support **labeled primary-key lookups** in `Barn.get()` when a `pk` grain exists

## Dynamic Models
- Declared when a `Cob` subclass has **no annotated fields**
- Allow new fields to be created at runtime via *direct attribute assignment* or `cob.__dna__.add_grain_dynamically(...)`
- Require fields to be passed by **keyword arguments** during initialization
- **Cannot use labeled lookups** in `Barn.get()` (key-based lookup only if autoenum is used)
- **Reject nested relationships** (child models in `one_to_many_grain` and `one_to_one_grain` must be static)


# Relationships: Nested Models

DataBarn supports hierarchical data structures using two relationship decorators:

## `@one_to_many_grain(label, ...)`

Declares a one-to-many relationship backed by a `Barn[ChildCob]`.

**Behavior:**
- The decorator registers metadata on the child `Cob` class
- During outer `Cob` class creation, a `Grain` is injected under `label`
- That grain has a `factory` that creates an empty `Barn` for the child model
- When you serialize, the outer cob's dictionary includes the child `Barn` as a list

**Constraints:**
- Child model must be **static** (not dynamic)
- Cannot be used on dynamic parent models

**Example:**
```python
class Order(Cob):
    order_id: int = Grain(pk=True)
    
    @one_to_many_grain("items")
    class Item(Cob):
        item_id: int = Grain(pk=True)
        name: str
```

## `@one_to_one_grain(label, ...)`

Declares a one-to-one relationship backed by a child `Cob` instance.

**Behavior:**
- A `Grain` is injected under `label`
- The grain expects a single instance of the child cob class
- Serialization includes the nested cob as a dictionary

**Constraints:**
- Child model must be **static**
- Cannot be used on dynamic parent models

## Parent Tracking

When a cob contains a child cob/barn (directly or via grain relationships), the child tracks its parent(s):
- `child.__dna__.latest_parent` — the most recently added parent
- Parent-cob association propagates to stored children in a `Barn`


# Data Access Ergonomics

## Attribute and Mapping Access

```python
# Attribute access
cob.field_name = value
value = cob.field_name
del cob.field_name

# Active field count
count = len(cob)

# `None` values still count; deleted grains do not

# Mapping access (grain labels only)
cob["field_name"] = value
value = cob["field_name"]
del cob["field_name"]

# Dictionary-like methods via __dna__
cob.__dna__.get(label, default=None)
cob.__dna__.update({"field": value})
cob.__dna__.pop(label)
for label, value in cob.__dna__.items():
    ...
```

## Containment and Traversal

```python
# Check if field has an active value (ignores deleted/unset)
if "field_name" in cob:
    ...

# Iterate over active field labels and values
for label in cob.__dna__.keys():
    ...
for label, value in cob.__dna__.items():
    ...
```

## Comparison Semantics

Comparisons (`==`, `!=`, `<`, `<=`, `>`, `>=`) work only on fields marked `comparable=True`:

```python
class Person(Cob):
    name: str = Grain(comparable=True)
    age: int = Grain(comparable=True)
    email: str  # not comparable

# Only name and age participate in comparisons
person1 < person2  # True only if all comparable fields in person1 are < person2
```

If no comparable fields exist, comparisons raise consistency errors (except identity equality `==` between the same instance).


# Conversion: Dict and JSON

DataBarn provides utilities to convert unstructured data into schema objects:

## `dict_to_cob(dikt, model=..., ...)`

Recursively converts a dictionary into a `Cob` instance.

**Behavior:**
- Nested dictionaries become nested `Cob` instances (based on schema metadata)
- Lists of dictionaries become `Barn` collections when the schema declares a child-barn relationship
- Type validation is applied according to grain type annotations
- Original dictionary keys are normalized to valid Python identifiers

**Key Normalization** (configurable):
- Replace spaces (`replace_space_with='_'`)
- Replace dashes (`replace_dash_with='__'`)
- Suffix Python keywords (`suffix_keyword_with='_'`)
- Prefix leading digits (`prefix_leading_num_with='n_'`)
- Replace invalid identifier characters (`replace_invalid_char_with='_'`)
- Suffix collisions with existing attributes (`suffix_existing_attr_with='_'`)
- Custom function (`custom_key_converter=callable`)

**Key Preservation:**
- Original keys are optionally stored via `Grain(key='original_key_name')`
- `cob.__dna__.to_dict()` re-emits original keys when serializing

## `json_to_cob(json_str, model=..., ...)`

Parses JSON text and converts it to a `Cob` instance using the same logic as `dict_to_cob`.


# Serialization

Each `Cob` provides serialization methods through its internal DNA:

```python
dict_output = cob.__dna__.to_dict()
json_output = cob.__dna__.to_json(**json_dumps_kwargs)
```

**Behavior:**
- Only **active grains** (set values that were not deleted) are included
- Serialization is **recursive**:
  - Nested `Cob` → nested dictionary
  - Nested `Barn` → list of dictionaries (in insertion order)
  - Lists/tuples containing cobs/barns → recursively serialized
- Serialized keys use `grain.key` (if present) or `grain.label` (field name)


# Validation and Constraints

## Runtime Type Validation

All values assigned to fields are validated against their type annotation using `beartype.door.is_bearable`:

```python
class User(Cob):
    age: int

user = User(age="not an int")  # Raises GrainTypeMismatchError
user.age = "not an int"        # Raises GrainTypeMismatchError (on assignment)

When validation fails due to business rules or custom checks (beyond simple type mismatches), raise `ValidationError` so callers can consistently detect and handle validation problems.
```

## Field Constraints

Constraints are enforced at initialization and assignment:

- **`required`**: Must be provided during init (unless a default/factory exists); raises `CobConstraintViolationError`
- **`frozen`**: Cannot be reassigned after first assignment; raises `CobConstraintViolationError`
- **`pk` / `autoenum`**: Primary key validation (uniqueness, not-null); enforced in `Barn.add()`
- **`unique`**: Value must not repeat in the same `Barn`; enforced on `Barn.add()`

When a runtime constraint or custom validation fails (for example, business-rule checks beyond type enforcement), prefer raising `ValidationError` so callers can consistently catch and handle validation problems.


# Error Taxonomy

DataBarn provides a structured exception hierarchy for precise diagnostics:

- **`DataBarnViolationError`** — base exception class
  - **`ValidationError`** — general validation failure for business-logic or custom checks; prefer raising this for user-facing validation issues
  - **`DataBarnSyntaxError`** — schema/API usage problems (invalid labels, malformed lookup args, wrong initialization mode)
  - **`CobConsistencyError`** — internal consistency issues in metaclass or runtime metadata
  - **`CobConstraintViolationError`** — required/frozen/pk/unique constraints fail
  - **`GrainTypeMismatchError`** — runtime type validation fails (via `beartype`)
    - **`SchemeViolationError`** — attempting dynamic operations on a static model
  - **`BarnConstraintViolationError`** — primary key or uniqueness constraints fail at the collection layer
  - **`GrainLabelError`** — invalid or ambiguous field names


# Technical Details

## Packaging and Environment

From `pyproject.toml`:

- **Package name**: `databarn`
- **Python requirement**: `>= 3.12`
- **Core dependency**: `beartype ~= 0.22` (runtime type validation)
- **Optional dev dependency**: `pytest >= 8`
- **License**: MIT
- **Build backend**: setuptools with PEP 621 (`pyproject.toml`)
- **Typing support**: Fully typed; `typing.Typed` classifier enabled

## Design Philosophy

DataBarn emphasizes:

- **Explicit invariants** — constraints and type validation are declared clearly
- **Understandable error messages** — custom exceptions with domain-specific context
- **Conversion convenience** — seamless dict/JSON ingestion with key normalization
- **Compositional modeling** — one-to-one and one-to-many relationships without external persistence
- **In-memory focus** — designed for runtime validation and serialization, not database I/O

## Performance and Concurrency Notes

- DataBarn is in-memory: operations such as `Barn.add` (with uniqueness checks), `find`, and `find_all` may require O(n) scans.
- Cobs and Barns are not synchronized for concurrent writes. Use external locking for multithreaded access.
- `find`/`find_all` return a new `Barn` with matching cob references, so the same cob can be registered in multiple barns.


# Intended Use Cases

DataBarn is optimized for:

- **Structured data ingestion** from dict/JSON with automatic key normalization
- **Strongly-constrained domain models** with explicit validation and relationship rules
- **Nested object graphs** (hierarchical data with one-to-one and one-to-many relationships)
- **Transformation pipelines** where dictionary serialization is required
- **Small to medium domain layers** where a full database-backed ORM would be overkill

## What DataBarn is NOT

DataBarn does not provide:

- Built-in database persistence or network I/O
- Asynchronous framework integration
- Query languages beyond simple in-memory attribute filtering
- Schema versioning or migrations
- Automatic relationship loading or lazy evaluation


# Minimal Example

```python
from databarn import Cob, Grain, Barn, one_to_one_grain, one_to_many_grain

class Order(Cob):
    order_id: int = Grain(pk=True)
    status: str = Grain(required=True, comparable=True)
    
    @one_to_one_grain("customer")
    class Customer(Cob):
        name: str = Grain(required=True)
        email: str = Grain(unique=True)
    
    @one_to_many_grain("items")
    class Item(Cob):
        item_id: int = Grain(pk=True)
        product_name: str = Grain(required=True)
        quantity: int = Grain(required=True)

# Create instances
customer = Order.Customer(name="Alice", email="alice@example.com")
order = Order(
    order_id=1,
    status="pending",
    customer=customer,)

# Add items to the nested Barn
order.items.add(Order.Item(item_id=1, product_name="Widget", quantity=5))
order.items.add(Order.Item(item_id=2, product_name="Gadget", quantity=2))

# Serialize to dictionary
order_dict = order.__dna__.to_dict()
# {
#   "order_id": 1,
#   "status": "pending",
#   "customer": {"name": "Alice", "email": "alice@example.com"},
#   "items": [
#     {"item_id": 1, "product_name": "Widget", "quantity": 5},
#     {"item_id": 2, "product_name": "Gadget", "quantity": 2},
#   ]
# }

# Store orders in a Barn
orders = Barn(Order)
orders.add(order)

# Retrieve by primary key
retrieved = orders.get(order_id=1)
assert retrieved.status == "pending"

# Convert from dict input
input_data = {
    "order_id": 2,
    "status": "shipped",
    "customer": {"name": "Bob", "email": "bob@example.com"},
    "items": [
        {"item_id": 1, "product_name": "Tool", "quantity": 1},
    ]
}
from databarn.funcs import dict_to_cob
order2 = dict_to_cob(input_data, model=Order)
orders.add(order2)
```

---
**Note for AIs:** This document describes DataBarn as it currently exists and functions. It is not a changelog. Updates to the project should be reflected here as changes to the current state description, not as historical "Recent Updates" sections. For a history of changes and commits, see [CHANGELOG.md](CHANGELOG.md).