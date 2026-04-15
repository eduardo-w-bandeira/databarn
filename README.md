# DataBarn

**Dictionary with Dot Notation • Schema definitions • Type validation • Lightweight in-memory ORM**

DataBarn is a Python library that combines the strictness of database schemas with the ergonomics of dictionaries. Define strongly-typed data models, validate values at runtime, and manage collections with primary key and uniqueness constraints—all while enjoying both dot-notation and dictionary-style access.

[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.8.1-orange.svg)](https://github.com/eduardo-w-bandeira/databarn)

## Features

- 🎯 **Dot-notation & dictionary access** — `cob.field` or `cob["field"]`
- ✨ **Strongly-typed models** using standard Python classes and type annotations
- 🔒 **Runtime validation** via `beartype` integration and custom constraints
- 📦 **Schema-driven collections** (`Barn`) with primary key and uniqueness enforcement
- 🔗 **Relationship support** for one-to-one and one-to-many hierarchical data
- 🔄 **Dict/JSON conversion** with schema preservation

## Installation
In the terminal, run the following command:

```bash
pip install git+https://github.com/eduardo-w-bandeira/databarn.git@v1.8.1
```

# You Choose: Dynamic or Static Data Carrier
```Python
from databarn import Cob, Grain

# Dynamic
dynamic_obj = Cob(name="VPN", value=7, open=True)

# Static: Verifying constraints
class Connection(Cob):
    name: str
    value: int
    open: bool

static_obj = Connection(name="VPN", value=7, open=True)
```

## What's the Purpose of a Dynamic Data Carrier?
It's a quick way to create an object that stores named values, which is useful for passing data between functions. Instead of using a dictionary, you can name the values and access them through the Dot Notation (object.attribute). For example:

#### Uncool Dictionary Solution
```Python
def get_anchor():
    ...
    return {"link": "www.example.com", "clickable": True, "text": "Bla"}

# Too bad: Accessing the values is inconvenient and ugly
dikt = get_anchor()
print(dikt["link"])
print(dikt["clickable"])
print(dikt["text"])
```

#### Cool Dynamic Data Carrier Solution
```Python
from databarn import Cob

def get_anchor():
    ...
    return Cob(link="www.example.com", clickable=True, text="Bla")

# Now you've created an object that holds its descriptive attributes
anchor = get_anchor()
print(anchor.clickable)
print(anchor.text)
print(anchor.link)
```

# Static Schema Definition

```Python
from typing import Any
from databarn import Cob, Grain

class Person(Cob):
    name: str = Grain(pk=True) # Defining a primary key is optional
    age: int  # DataBarn will check the type

# Instantiate it like this
person1 = Person(name="George", age=25)

# Or you can use positional arguments
person2 = Person("Bob", 31)
person3 = Person("Jim", 25)
```

# In-memory ORM

```Python
# Create a Barn-object with the Cob-model you defined
persons = Person.__dna__.create_barn()

persons.add(person1)  # Barn stores in order
persons.add(person2)
persons.add(person3)

# Retrieving in order all cobs from Barn
print("All persons in the Barn:")
for person in persons:
    print(person)

# Retrieving a specific cob by its key
george = persons.get("George")
print(george)

# Finding cobs based on criteria
results = persons.find_all(age=25)
# find_all() returns a Barn object populated \
# with the cobs that were found
print("Persons matching criteria (age 25):")
for person in results:
    print(person)

# Finding the first cob based on criteria
match_person = persons.find(name="Jim", age=25)

# Count cobs in the barn
count = len(persons)

# Get cob by index
first_person = persons[0]

# Get a Barn subset by slice
persons_subset = persons[1:3]

# Removing a cob from the Barn
persons.remove(match_person)
```

## What's The Purpose of an In-memory ORM

Barns offer ORM-like capabilities, allowing for easy storage, retrieval, and manipulation of objects (cobs) in memory without the overhead of a full database.

## Performance and scale

DataBarn keeps everything in memory. Operations such as `Barn.add` when `unique=True` is used, or `find` / `find_all`, may scan existing cobs—often **O(n)** work per call. That fits small and medium in-process datasets; it is not a substitute for a database at large scale.

**Thread safety:** Cobs and barns are not synchronized. If you share them across threads, use external locking or confine each structure to a single thread.

## Multiple barns and `find_all`

`find` and `find_all` build a **new** `Barn` and call `add` for each matching cob. The same cob instance can therefore be registered in **more than one** barn at a time (see `cob.__dna__.barns`). Removing a cob from one barn does not remove it from the others.

## Grain Definitions

```Python
from typing import Any
from databarn import Cob, Grain

class Line(Cob):

    number: int = Grain(pk=True, autoenum=True)
        # type is int, so DataBarn will check it for validity
        # pk => Is primary key? [optional]
        # autoenum => Barn will assign automatically with an incrementing number
    
    original: str = Grain(frozen=True, required=True)
        # frozen=True => the value cannot be changed after assigned
        # required=True => a value must be provided at Cob init (unless default/factory)
    
    string: str = "Bla"
        # default => value to be automatically assigned when no value is provided
        # The default value is None by default

    note: bool | str | None = None
        # For multiple types, use the pipe operator
        # If None should be accepted, include None in the type annotation
        # and assign an initial value (for example: None)

    processed: Any = Grain(unique=True)
        # If you want to accept any type, annotate as Any
        # unique=True => the value must be unique in the barn


text = """Lorem ipsum dolor sit amet, consectetur adipiscing elit,
sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam,
quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
Excepteur sint occaecat cupidatat non proident,
sunt in culpa qui officia deserunt mollit anim id est laborum."""

# Create your Barn
lines = Line.__dna__.create_barn()

for content in text.split("\n"):
    line = Line(original=content, processed=content+" is at line: ")
    lines.add(line)
    # Once you have added it to Barn, the autoenum grain will be assigned
    line.processed += str(line.number)
    print(line)
```

## Grain Definition Constraints
1. `type annotation`: Assigning a value of a different type than the annotated for the grain will raise an error. More details in [Type Checking](#type-checking).
2. `optional initial value`: Grains are optional by default. If no initial value is provided during Cob initialization or defined in the Cob-model (via `default=...`, `factory=...`, or direct assignment), the Grain attribute will not be created, thus Cob will raise AttributeError if tried to access it. You can explicitly require an initial value using `required=True` in the Grain definition.
3. `pk=True`: Is Primary key?
    - Assigning a non-unique value to the key grain will raise an error in Barn. `None` is a valid primary-key value, but it still must be unique within a Barn. After it has been appended to a Barn, the key value becomes immutable (frozen).
    - For a composite key, define more than one grain as a key.
4. `autoenum=True`: Automatic incremental integer number.
5. `frozen=True`: Altering the value of a frozen grain after its first assignment will raise an error. If it has not been assigned yet, one initial assignment is still allowed.
6. `required=True`: A value must be provided at the Cob initialization.
7. `unique=True`: Assigning a value that already exists for that grain in the barn will raise an error in the Barn. `None` is treated like any other value for uniqueness checks, so duplicate `None` values also violate uniqueness.
8. `comparable=True`: Enables comparison operations (==, !=, <, >, <=, >=) between cobs based on their comparable grain values.
9. `factory=callable`: Uses a callable to generate the default value for the grain when no value is provided at instantiation time.

## Type Checking
To check the types of values assigned to grains during code execution, DataBarn relies on the [beartype](https://github.com/beartype/beartype) library, a runtime type checker. It supports arbitrary type annotations (e.g., List[str], Dict[str, float], int, Union, etc.) for type checking. The following rules apply:
1. If the value doesn't match the type annotation, DataBarn will raise an error.
2. `None` is accepted only when the type annotation explicitly allows it (for example: `str | None`, `Optional[str]`, or `Any`).


## There's Only One Reserved Name: `__dna__`
The only attribute name you cannot use in your Cob-model is `__dna__`. This approach was used to avoid name clashes when converting from json/dict, as well as to avoid polluting your namespace. All metadata and utility methods are stored in the `__dna__` object.

## There's Only One Special Method Name: `__post_init__`
You can define a `__post_init__` method in your Cob-derived class to execute custom logic after the object is instantiated:

```Python
from databarn import Cob, Grain

class Person(Cob):
    name: str
    license: int
    
    def __post_init__(self):
        # Custom initialization logic
        print(f"Person created: {self.name}")

person = Person(name="Alice", license=987)
# Output: Person created: Alice
```

This method is called automatically after all grains have been initialized, making it useful for computed properties, validation, or side effects.

# Magically Creating Child Entities
For the magical approach, use the decorator `one_to_many_grain()`:
```Python
from databarn import Cob, one_to_many_grain, Barn, Grain

class Person(Cob):
    name: str = Grain(required=True)
    telephones: Barn

    @one_to_many_grain("telephones")
    class Telephone(Cob):
        number: int = Grain(pk=True)

person = Person(name="John")
# It automatically creates a sub-barn called 'telephones', instantiated as Barn(Telephone).
person.telephones.add(Person.Telephone(number=76543321))
```

## Accessing the Parent Via Child
For accessing the parent, use `child.__dna__.latest_parent`. For example:

```Python
telephone = person.telephones[0]
parent = telephone.__dna__.latest_parent
print("Is 'John' the parent:", (parent is person)) # Outputs True 
```

## Converting a Cob to a Dictionary
```Python
from databarn import Cob, Grain

class Person(Cob):
    name: str = Grain(required=True)
    age: int

person = Person(name="Ada", age=36)
dikt = person.__dna__.to_dict()
```
It's recursive, thus it will convert all children and any single child to dict as well.

## Converting a Cob to a Json String
```Python
s_json = person.__dna__.to_json()
```

## What If You Don't Define a Key?
In this case, Barn will use `Cob.__dna__.autoid` as the key, which is the Python `id()` number.

```Python
from databarn import Cob, Grain
from datetime import date

class Student(Cob):
    name: str = Grain(required=True)
    phone: int
    enrolled: bool = Grain(default=False)
    birthdate: date = Grain(required=True)


students = Student.__dna__.create_barn()

student = Student(name="Rita", phone=12345678,
                  enrolled=True, birthdate=date(1998, 10, 27))

students.add(student)

# Accessing autoid
student_id = student.__dna__.autoid # The Python object id

# The method `get()` will use the autoid value
some_student = students.get(student_id)
print(some_student is student) # Outputs True
```

# Converting a Dictionary to a Cob
You can easily convert a dictionary to a `Cob` object using the `create_cob_from_dict` method:
```Python
from databarn import Cob

book_dict = {
    "title": "1984",
    "author": "George Orwell",
    "pages": 328
}

book = Cob.__dna__.create_cob_from_dict(book_dict)
print(book.title)  # Outputs: 1984
```

## Converting a Dictionary to a Cob using a Cob-Model
You can also convert a dictionary to a `Cob` object while enforcing a specific model structure using a Cob-derived class:
```Python
from databarn import Cob

class Book(Cob):
    title: str = Grain(required=True)
    author: str
    pages: int

book_dict = {
    "title": "1984",
    "author": "George Orwell",
    "pages": 328
}

book = Book.__dna__.create_cob_from_dict(book_dict)
print(book.title)  # Outputs: 1984
print(type(book))  # Outputs: <class 'Book'>
```

DataBarn will validate the dictionary values against the Cob model's type annotations and grain constraints. If validation fails, an error will be raised.


## Recursive Conversion of Nested Structures

The conversion process is recursive: any sub-dictionary will also be converted to `Cob` objects. Lists containing dictionaries will be converted to `Barn` objects, and their dictionaries will become `Cob` objects. This means you can access nested data using dot notation at any depth.

For example:

```Python
book_dict = {
    "title": "1984",
    "author": {"first": "George", "last": "Orwell"},
    "reviews": [
        {"user": "alice", "rating": 5},
        {"user": "bob", "rating": 4}
    ]
}

book = Cob.__dna__.create_cob_from_dict(book_dict)
print(book.author.first)         # Output: George
print(book.reviews[0].user)      # Output: alice
```


## Automatic key conversion
When converting a dictionary to a Cob, DataBarn converts keys to valid Python attribute names using configurable rules. By default, spaces become `_`, dashes become `__`, Python keywords get a trailing `_`, and leading digits get an `n_` prefix.

For instance, a key like `"this key"` will become `this_key`:

```Python
book_dict = {
    "this key": 71.2,
    "another-key": 123
}

book = Cob.__dna__.create_cob_from_dict(book_dict)
print(book.this_key)      # Output: 71.2
print(book.another__key)   # Output: 123
```

This ensures all attributes are accessible using standard dot notation.

### Converting a Cob Back to a Dictionary

When you convert a `Cob` object back to a dictionary using `to_dict()`, DataBarn restores the original key names as they appeared in the source dictionary. This means that even if attribute names were transformed to valid Python identifiers internally, the output dictionary will use the original keys.

```Python
dikt = book.__dna__.to_dict()
print(dikt)
# Output: {'this key': 71.2, 'another-key': 123}
```

This ensures round-trip integrity between dictionaries and Cob objects.

# Converting a JSON String to a Cob

You can also convert JSON strings directly to `Cob` objects using the `json_to_cob` function:

```Python
from databarn import json_to_cob

json_str = '''
{
    "title": "1984",
    "author": "George Orwell",
    "pages": 328
}
'''

book = json_to_cob(json_str)
print(book.title)  # Outputs: 1984
```

This works the same way as `dict_to_cob()`, with all the same recursive conversion features and automatic key conversion capabilities. You can pass additional keyword arguments to `json_to_cob()` that will be forwarded to `json.loads()`.

## Converting a JSON String to a Cob using a Cob-Model

If you want to validate and map JSON directly into a specific model, use `create_cob_from_json`:

```Python
from databarn import Cob, Grain

class Book(Cob):
    title: str = Grain(required=True)
    author: str
    pages: int

json_str = '''
{
    "title": "1984",
    "author": "George Orwell",
    "pages": 328
}
'''

book = Book.__dna__.create_cob_from_json(json_str)
print(book.title)  # Outputs: 1984
print(type(book))  # Outputs: <class 'Book'>
```

# Dynamic Grain Management, but declaring a type

For dynamic Cobs, you can add and remove grains at runtime:

```Python
from databarn import Cob, Grain

cob = Cob()

cob.__dna__.add_grain_dynamically("score", type=int, grain=Grain())
cob.score = 7.5  # Raises GrainTypeMismatchError
cob.score = 75  # Fine

# Remove a grain dynamically
del cob.score # or del cob["score"]
```

Note: You can only add/remove grains on dynamic Cobs. Attempting this on a static (model-based) Cob will raise a `StaticModelViolationError`.

# Comparing Cobs

Cobs support comparison operations based on their `comparable` grains:

```Python
from databarn import Cob, Grain

class Product(Cob):
    name: str
    price: float = Grain(comparable=True)

product1 = Product(name="Widget", price=10.5)
product2 = Product(name="Gadget", price=20.0)

print(product1 < product2)   # True, because 10.5 < 20.0
print(product1 == product2)  # False
print(product1 <= product2)  # True
print(product1 > product2)   # False
```

**Important:** To use comparison operations, at least one grain must be marked with `comparable=True`. If no comparable grains are defined, comparison operations will raise a `CobConsistencyError`.

## Comparison Rules:
- `__eq__` (==): All comparable grains must be equal
- `__ne__` (!= ): At least one comparable grain must differ
- `__lt__` (<): All comparable grains in self must be less than those in the other cob
- `__le__` (<=): All comparable grains in self must be less than or equal to those in the other cob
- `__gt__` (>): All comparable grains in self must be greater than those in the other cob
- `__ge__` (>=): All comparable grains in self must be greater than or equal to those in the other cob

# Barn Additional Methods

## Adding Multiple Cobs

```Python
# Using add_all() to add multiple cobs at once
persons.add_all(person1, person2, person3)

# Using append() - similar to add() but returns None
persons.append(person1)
```

## Checking for Primakey Existence

```Python
# Check if a primakey exists in the Barn
if persons.has_primakey("George"):
    print("George is in the barn")

# For composite keys, use multiple arguments
results_barn.has_primakey(1, "John")  # For composite key
```

## Barn Membership

```Python
# Check if a cob is in the Barn using 'in'
if person1 in persons:
    print("Person is in the barn")

# Get Barn string representation
print(persons)  # Output: Barn(3 cobs)
```

## Barn Slicing

```Python
# Get a subset of cobs using slicing
subset = persons[1:3]  # Returns a new Barn with cobs at indices 1 and 2
first_person = persons[0]  # Returns the first cob directly
```

# Dictionary-like Access for Cobs

You can access and modify cob attributes using dictionary-like syntax:

```Python
from databarn import Cob, Grain

class Book(Cob):
    title: str = Grain(required=True)
    author: str
    pages: int

book = Book(title="1984", author="George Orwell", pages=328)

# Dictionary-like access
print(book["title"])       # Outputs: 1984
print(book["author"])      # Outputs: George Orwell

# Dictionary-like assignment (existing grains on a static model)
book["pages"] = 350

# Check if a grain exists using 'in'
if "title" in book:
    print("Title exists")
```

On a **static** model, only grains defined on the class can be used; adding a new name raises `StaticModelViolationError`. On a **dynamic** `Cob()`, you can add and remove grains with the same syntax:

```Python
cob = Cob(title="Notes")
cob["rating"] = 5.0
print(cob["rating"])   # Outputs: 5.0
del cob["rating"]
```

This allows you to treat Cobs like dictionaries while maintaining type checking and validation where the model allows it.

# Iterating Over Cob Attributes

```Python
from databarn import Cob, Grain

class Person(Cob):
    name: str
    age: int
    email: str

person = Person(name="John", age=30, email="john@example.com")

# Iterate over all attributes as (label, value) pairs
for label, value in person.__dna__.items():
    print(f"{label}: {value}")
    # Output:
    # name: John
    # age: 30
    # email: john@example.com
```

# Accessing Grains and Grists

You can access grain and grist information programmatically:

```Python
from databarn import Cob, Grain

class Student(Cob):
    name: str = Grain(required=True)
    grade: int = Grain(default=0)

student = Student(name="Alice")

# Get a grain by label (class-level)
grain = Student.__dna__.get_grain("name")
print(grain.required)  # True

# Get a grist by label (instance-level)
grist = student.__dna__.get_grist("name")
print(grist.get_value())  # Alice

# Get all grists
for grist in student.__dna__.grists:
    print(f"{grist.label}: {grist.get_value()}")
```

# Child Cob Grain

Similar to `one_to_many_grain()`, you can define a Cob-model as a sub-Cob grain:

```Python
from databarn import Cob, one_to_one_grain

class Person(Cob):
    name: str

    @one_to_one_grain("address")
    class Address(Cob):
        street: str
        city: str


person = Person(name="John")
person.address = Person.Address(street="123 Main St", city="New York")
print(person.address.city)  # Output: New York
```

The main difference from `one_to_many_grain()`:
- With `one_to_many_grain()`: Automatically creates and manages a Barn
- With `one_to_one_grain()`: You manually assign a single Cob instance
