# DataBarn
*DataBarn* is a simple in-memory ORM and data carrier for Python, featuring a powerful type checker. It also has a pretty cool function to convert dictionaries (and JSONs) into Python attributes, so they can be manipulated through dot notation.

## Installation
In the terminal, run the following command:

```bash	
pip install git+https://github.com/eduardo-w-bandeira/databarn.git
```

# You Choose: Dynamic or Static Data Carrier
```Python
from databarn import Cob, Grain

# Dynamic
dynamic_obj = Cob(name="VPN", value=7, open=True)

# Static: Verifying constraints
class Connection(Cob):
    name: str = Grain()
    value: int = Grain()
    open: bool = Grain()

static_obj = Connection(name="VPN", value=7, open=True)
```

## What's the Purpose of a Dynamic Data Carrier?
It's a quick way to create an object that stores named values, which is useful for passing data between functions. Instead of using a tuple with the values, you can name the values and access them through the Dot Notation (object.attribute). For example:

#### [Uncool] Tuple Solution
```Python
def get_anchor():
    ...
    return "www.example.com", True, "Bla"

# Too bad: You have to match the order, and deal with loose attributes
link, clickable, text = get_anchor()
```

#### [Cool] Dynamic Data Carrier Solution
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

# Static Data Carrier

```Python
from databarn import Cob, Grain

class Person(Cob):
    name: str = Grain(pk=True) # Defining a primary key is optional
    age: int = Grain() # DataBarn will check the type

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

## Grain Definitions

```Python
from databarn import Cob, Grain

class Line(Cob):

    number: int = Grain(pk=True, auto=True)
        # type is int, so DataBarn will check it for validity
        # pk => Is primary key? [optional]
        # auto => Barn will assigned automatically with an incrementing number
    
    original: str = Grain(frozen=True, required=True)
        # frozen=True => the value cannot be changed after assigned
        # required=True => the value cannot be None
    
    string: str = Grain(default="Bla")
        # default => value to be automatically assigned when no value is provided
        # The default value is None by default

    note: bool | str = Grain()
        # For multiple types, use the pipe operator

    processed = Grain(unique=True)
        # If no type is specified, any type will be accepted
        # unique=True => the value must be unique in the barn


text = """Lorem ipsum dolor sit amet, consectetur adipiscing elit,
sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam,
quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.
Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.
Excepteur sint occaecat cupidatat non proident,
sunt in culpa qui officia deserunt mollit anim id est laborum."""

# Create your Barn
lines = Lines.__dna__.create_barn()

for content in text.split("\n"):
    line = Line(original=content, processed=content+" is at line: ")
    lines.add(line)
    # Once you have added it to Barn, the auto grain will be assigned
    line.processed += str(line.number)
    print(line)
```

## Grain Definition Constraints
1. `type annotation`: Assigning a value of a different type than the annotated for the grain will raise an error. More details in [Type Checking](#type-checking).
2. `auto=True`: Automatic incremental integer number. Altering the value of an auto grain will raise an error.
3. `frozen=True`: Altering the value of a frozen grain, after it has been assigned, will raise an error. It is mandatory to assign it when instantiating your Cob-derived class; otherwise, its value will be frozen to the default value.
4. `pk=True`: Is Primary key?
    - Assigning None or a non-unique value to the key grain will raise an error in Barn. After it has been appended to a Barn, the key value becomes immutable (frozen).
    - For a composite key, define more than one grain as a key.
6. `required=True`: Assigning None value to the grain will raise an error.
7. `unique=True`: Assigning a value that already exists for that grain in the barn will raise an error in the Barn. None value is allowed for unique grains (but not for key grains).
8. `comparable=True`: Enables comparison operations (==, !=, <, >, <=, >=) between cobs based on their comparable grain values.

## Type Checking
To check the types of values assigned to grains during code execution, DataBarn relies on the [typeguard](https://github.com/agronholm/typeguard/) library, a runtime type checker. It supports arbitrary type annotations (e.g., List[str], Dict[str, float], int, Union, etc.) for type checking. The following rules apply:
1. If the value doesn't match the type annotation, DataBarn will raise an error.
2. None values are always accepted, regardless of the type annotation. If you want to enforce a non-None value, use `required=True` in the Grain definition.
3. If the type annotation is a Union, the value must match at least one of the types in the Union.
4. If you don't define a type annotation, any value will be accepted.


# There's Only One Protected Name: `__dna__`
The only attribute name you cannot use in your Cob-model is `__dna__`. This approach was used to avoid name clashes when converting from json/dict, as well as to avoid polluting your namespace. All meta data and utillity methods are stored in the `__dna__` object.


# Magically Creating Child Entities
For the magical approach, use the decorator `wiz_create_child_barn()`:
```Python
from databarn import Cob, wiz_create_child_barn

class Person(Cob):
    name: str = Grain()

    @wiz_create_child_barn("telephones")
    class Telephone(Cob):
        number: int = Grain(pk=True)

person = Person(name="John")
# It automatically creates a sub-barn called 'telephones', instantiated as Barn(Telephone).
person.telephones.add(Person.Telephones(number=76543321))
```

## Accessing the Parent Via Child
For acessing the parent, use `child.__dna__.parent`. For example:

```Python
telephone = person.telephones[0]
parent = telephone.__dna__.parent
print("Is 'John' the parent:", (parent is person)) # Outputs True 
```

## Converting a Cob to a Dictionary
```Python
dikt = kathryn.__dna__.to_dict()
```
It's recursive, thus it will convert all children and any single child to dict as well.

## Converting a Cob to a Json String
```Python
s_json = kathryn.__dna__.to_json()
```

## What If You Don't Define a Key?
In this case, Barn will use `Cob.__dna__.autoid` as the key, which is the Python `id()` number.

```Python
from databarn import Cob, Grain
from datetime import date

class Student(Cob):
    name: str = Grain(required=True)
    phone: int = Grain()
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
You can easily convert a dictionary to a `Cob` object using the `dict_to_cob` function:
```Python
from databarn import dict_to_cob

book_dict = {
    "title": "1984",
    "author": "George Orwell",
    "pages": 328
}

book = dict_to_cob(book_dict)
print(book.title)  # Outputs: 1984
```

## Recursive Conversion of Nested Structures

The conversion process is recursive: any sub-dictionary will also be converted to `Cob` objects. Lists containing dictionaries will be converted do `Barn` objects, and their dictationaries will become `Cob` objects. This means you can access nested data using dot notation at any depth.

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

book = dict_to_cob(book_dict)
print(book.author.first)         # Output: George
print(book.reviews[0].user)      # Output: alice
```


## Automatic key conversion
When converting a dictionary to a Cob, DataBarn will automatically convert keys to valid Python attribute names. For example, dictionary keys containing spaces or special characters will be transformed to underscore_case. 

For instance, a key like `"this key"` will become `this_key`:

```Python
book_dict = {
    "this key": 71.2,
    "another-key": 123
}

book = dict_to_cob(book_dict)
print(book.this_key)      # Output: value
print(book.another__key)   # Output: 123
```

This ensures all attributes are accessible using standard dot notation.

### Converting a Cob Back to a Dictionary

When you convert a `Cob` object back to a dictionary using `to_dict()`, DataBarn restores the original key names as they appeared in the source dictionary. This means that even if attribute names were transformed to valid Python identifiers internally, the output dictionary will use the original keys.

```Python
dikt = book.__dna__.to_dict()
print(dikt)
# Output: {'this key': 'value', 'another-key': 123}
```

This ensures round-trip integrity between dictionaries and Cob objects.