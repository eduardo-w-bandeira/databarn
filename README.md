# Data Barn
**Data Barn** is a simple in-memory ORM and data carrier, for Python.

# Using Data Barn As a Data Carrier

```Python
from databarn import Seed

obj = Seed(name="VPN", value=7, open=True)

print(obj.name, obj.value, obj.open)
```

## What's the Purpose of a Data Carrier?

A data carrier is a quick way to create an object that stores named values, which is useful for passing data between functions. Instead of using a tuple with the values, you can name the values and access them through the Dot Notation (object.attribute). This approach improves code readability by providing a way to access values using descriptive cell names instead of integer indices. For example:

**(Uncool) Tuple Solution**

```Python

def get_anchor():
    ...
    return ("www.example.com", False, "Bla")

# With tuples, you have to use indices, match the order, and deal with the names
link, is_clickable, text = get_anchor()
```

**(Cool) Data Carrier Solution**

```Python
from databarn import Seed

def get_anchor():
    ...
    return Seed(link="www.example.com", is_clickable=False, text="Bla")

# Now you've created an object that holds its descriptive attributes
anchor = get_anchor()
# Use meaningful object descriptions in any order
print(anchor.is_clickable)
print(anchor.text)
print(anchor.link)
```

# Using Data Barn As an In-memory ORM

```Python
from databarn import Seed, Cell, Barn

class Person(Seed):
    name = Cell(str, is_key=True) # primary key is optional
    age = Cell(int)

# Instantiate it like this
person1 = Person(name="George", age=25)

# Or you can use positional arguments
person2 = Person("Bob", 31)

# Or assign attributes later
person3 = Person()
person3.name = "Jim"
person3.age = 25

# Adding objects to the Barn
barn = Barn()

barn.add(person1)  # Barn stores in order
barn.add(person2)
barn.add(person3)
```

### Working With Barn Objects

```Python
# Retrieving in order all objects from Barn
print("All persons in the Barn:")
for person in barn:
    print(person)

# Retrieving a specific object by primary key
george = barn.get("George")
print(george)

# Finding objects based on criteria
results = barn.find_all(age=25)
print("Persons matching criteria (age 25):")
for person in results:
    print(person)

# Finding the first object based on criteria
match_person = barn.find(name="Jim", age=25)

# Removing an object from the Barn
barn.remove(match_person)
print("Remaining persons after removal:")
for person in barn:
    print(person)

# Accessing attributes directly
print("Accessing attributes directly:")
print(f"Name of person1: {person1.name}")
print(f"Age of person1: {person1.age}")
```

## What's The Purpose of an In-memory ORM

Barn is intended to be a smart alternative to lists, dictionaries, or even NamedTuple. It's a tool to manage multiple objects that have named attributes.

## Cell Definitions

```Python
from databarn import Seed, Cell, Barn

class Line(Seed):

    # Using a primary key is optional.
    # An autoincrement cell means that Barn will automatically \
    # assign an incremental integer number.
    number = Cell(int, is_key=True, autoincrement=True)

    # A frozen cell cannot be modified after the value is assigned.
    original = Cell(str, frozen=True)
    
    # If the type is not defined, any type will be accepted.
    processed = Cell()
    
    # The default value is set to None.
    # If a value is not provided when instantiating the cell, \
    # the default value will be used.
    string = Cell(str, default="Bla")
    
    # For multiple types, use a tuple of types.
    note = Cell(type=(bool, str)) # Or just `Cell((bool, str))`


barn = Barn()

text = """Aaaa
Bbbb
Cccc"""

for content in text.split("\n"):
    line = Line(original=content, processed=content+" is at line: ")
    barn.add(line)
    # Once you have added it to Barn, the autoincrement cell will be assigned
    line.processed += str(line.number)
    print(line)
```

## Cell Definition Constraints

1. TYPE: Assigning a value of a different type than the defined cell type will raise a `TypeError`. However, `None` is always accepted.
2. AUTOINCREMENT: Altering the value of an autoincrement cell will raise an `AttributeError`.
3. FROZEN: Altering the value of a frozen cell, after it has been assigned, will raise an `AttributeError`. It is mandatory to assign it when instantiating your Seed model; otherwise, its value will be frozen to `None`.
4. IS_KEY: Assigning `None` or a non-unique value to the primary key cell will raise a `ValueError`. Nevertheless, the primary key value is *mutable*.
5. IS_KEY: Defining multiple primary keys will raise a `ValueError`.

## What If You Don't Define a Primary Key?

In this case, Barn will use `autoid` as the primary key, which is an auto-generated incremental integer number that starts at one.

```Python
from databarn import Seed, Cell, Barn

class Student(Seed):
    name = Cell(str)
    phone = Cell(int)
    enrolled = Cell(bool)

student = Student(name="Rita", phone=12345678, enrolled=True)

barn = Barn()
barn.add(student)

# Accessing autoid
print(student.wiz.autoid) # Outuputs 1

# The method `get()` will use the autoid value
obj = barn.get(1)
print(obj is student) # Outputs True
```

## Accessing the Magic Attributes

```Python
# Using the last example as basis:
print(student.wiz.name_cell_map) # Outputs a dictionary containing each cell_name and its cell_instance.
print(student.wiz.autoid) # Outputs the auto-generated incremental integer id (even if not used).
print(student.wiz.barn) # Outputs the Barn where the object is stored.
print(student.wiz.key_name) # Outputs either the primary key attribute name or None (if not provided).
print(student.wiz.key) # Outputs the primary key value (which may be user-defined or `autoid`).
```

After being removed from the Barn, `barn` will be rolled back to None. For example:
```Python
barn.remove(student)
print(student.wiz.barn) # Outputs None
```