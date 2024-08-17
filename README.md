# Data Barn
**Data Barn** is a simple in-memory ORM and data carrier for Python.

# Quick Data Carrier

```Python
from databarn import Seed

my_obj = Seed(name="VPN", value=7, open=True)

print(my_obj.name, my_obj.value, my_obj.open)
```

## What's the Purpose of a Data Carrier?

It's a quick way to create an object that stores named values, which is useful for passing data between functions. Instead of using a tuple with the values, you can name the values and access them through the Dot Notation (object.attribute). For example:

#### (Uncool) Tuple Solution

```Python

def get_anchor():
    ...
    return ("www.example.com", False, "Bla")

# Too bad: You have to match the order, and deal with loose attributes
link, clickable, text = get_anchor()
```

#### (Cool) Data Carrier Solution

```Python
from databarn import Seed, Barn

def get_anchor():
    ...
    return Seed(link="www.example.com", clickable=False, text="Bla")

# Now you've created an object that holds its descriptive attributes
anchor = get_anchor()
print(anchor)
print(anchor.clickable)
print(anchor.text)
print(anchor.link)

# If you have to handle multiple objects, you can store them in a Barn
barn = Barn()
barn.append(anchor) # More details below
```


# In-memory ORM

```Python
from databarn import Seed, Cell, Barn

class Person(Seed):
    name = Cell(str, key=True) # Defining a key is optional
    age = Cell(int)

# Instantiate it like this
person1 = Person(name="George", age=25)

# Or you can use positional arguments
person2 = Person("Bob", 31)
person3 = Person("Jim", 25)

# To ensure consistency, pass your Seed-like class \
# when creating a Barn instance.
barn = Barn(Person)

barn.append(person1)  # Barn stores in order
barn.append(person2)
barn.append(person3)
```

### Working With Barn Seeds

```Python
# Retrieving in order all seeds from Barn
print("All persons in the Barn:")
for person in barn:
    print(person)

# Retrieving a specific seed by its key
george = barn.get("George")
print(george)

# Finding seeds based on criteria
results = barn.find_all(age=25)
# find_all() returns a new Barn() object populated \
# with the seeds that were found
print("Persons matching criteria (age 25):")
for person in results:
    print(person)

# Finding the first seed based on criteria
match_person = barn.find(name="Jim", age=25)

# Count seeds in the barn
count = len(barn)

# Get seed by index
first_person = barn[0]

# Removing a seed from the Barn
barn.remove(match_person)
```

## What's The Purpose of an In-memory ORM

Barn is intended to be a smart blend of a dictionary, list, SimpleNamespace and dataclass. It's a tool to manage multiple objects that have named attributes.

## Cell Definitions

```Python
from databarn import Seed, Cell, Barn

class Line(Seed):

    # Using a key is optional.
    # An auto cell means that Barn will automatically \
    # assign an incremental integer number.
    number = Cell(int, key=True, auto=True)

    # A frozen cell cannot be modified after the value is assigned.
    # If `none` is false, you have to provide \
    # the value when instatiating it.
    original = Cell(str, frozen=True, none=False)
    
    # If the type is not defined, any type will be accepted.
    processed = Cell()
    
    # The default value is set to None, \
    # unless you define other value.
    string = Cell(str, default="Bla")
    
    # For multiple types, use a tuple of types.
    note = Cell(type=(bool, str)) # Or Cell((bool, str))


text = """Aaaa
Bbbb
Cccc"""

# Create your Barn
barn = Barn(Seed)

for content in text.split("\n"):
    line = Line(original=content, processed=content+" is at line: ")
    barn.append(line)
    # Once you have added it to Barn, the auto cell will be assigned
    line.processed += str(line.number)
    print(line)
```

## Cell Definition Constraints

1. `type`: Assigning a value of a different type than the defined cell type will raise a TypeError in Seed. However, None is always accepted.
2. `auto=True`: Altering the value of an auto cell will raise an AttributeError.
3. `frozen=True`: Altering the value of a frozen cell, after it has been assigned, will raise an AttributeError in Seed. It is mandatory to assign it when instantiating your Seed-derived class; otherwise, its value will be frozen to None.
4. `key=True`:
    - Assigning None or a non-unique value to the key cell will raise a ValueError in Barn. Nevertheless, the key value is *mutable*.
    - Defining multiple keys will raise a ValueError when instantiating your Seed-derived class.
6. `none=False`: Setting None will raise ValueError in Seed.

## What If You Don't Define a Key?

In this case, Barn will use `Seed.dna.autoid` as the key, which is an auto-generated incremental integer number that starts at one.

```Python
from databarn import Seed, Cell, Barn

class Student(Seed):
    name = Cell(str)
    phone = Cell(int)
    enrolled = Cell(bool)

student = Student(name="Rita", phone=12345678, enrolled=True)

barn = Barn()
barn.append(student)

# Accessing autoid
print(student.dna.autoid) # Outuputs 1

# The method `get()` will use the autoid value
seed = barn.get(1)
print(seed is student) # Outputs True
```

## There's only one protected name: `dna`
The only attribute name you cannot use in your Seed model is `dna`. This approach was used to avoid polluting your namespace. All utillity methods and meta data are stored in the `dna` object.