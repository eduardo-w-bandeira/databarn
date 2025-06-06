# DataBarn
*DataBarn* is a simple in-memory ORM and data carrier for Python. It also has a pretty cool type checker.

## Installation
In the terminal, navigate to the directory containing the `databarn` and run the following command:

```bash	
pip3 install .
```

# You Choose: Dynamic or Static Data Carrier
```Python
from databarn import Seed, Field

# Dynamic
dynamic_obj = Seed(name="VPN", value=7, open=True)

# Static: Verifying constraints
class Connection(Seed):
    name: str = Field()
    value: int = Field()
    open: bool = Field()

static_obj = Connection(name="VPN", value=7, open=True)
```

## What's the Purpose of a Dynamic Data Carrier?
It's a quick way to create an object that stores named values, which is useful for passing data between functions. Instead of using a tuple with the values, you can name the values and access them through the Dot Notation (object.attribute). For example:

#### (Uncool) Tuple Solution
```Python
def get_anchor():
    ...
    return "www.example.com", True, "Bla"

# Too bad: You have to match the order, and deal with loose attributes
link, clickable, text = get_anchor()
```

#### (Cool) Dynamic Data Carrier Solution
```Python
from databarn import Seed, Barn

def get_anchor():
    ...
    return Seed(link="www.example.com", clickable=True, text="Bla")

# Now you've created an object that holds its descriptive attributes
anchor = get_anchor()
print(anchor.clickable)
print(anchor.text)
print(anchor.link)
```

#### If you have to handle multiple objects, you can store them in a Barn
```Python
anchors = Barn()
anchors.append(anchor) # More details below
```


# Static Data Carrier

```Python
from databarn import Seed, Field, Barn

class Person(Seed):
    name: str = Field(key=True) # Defining a key is optional
    age: int = Field() # DataBarn will check the type

# Instantiate it like this
person1 = Person(name="George", age=25)

# Or you can use positional arguments
person2 = Person("Bob", 31)
person3 = Person("Jim", 25)
```

# In-memory ORM

```Python
# To ensure consistency, pass your Seed-like class \
# when creating a Barn instance.
persons = Barn(Person)

persons.append(person1)  # Barn stores in order
persons.append(person2)
persons.append(person3)

# Retrieving in order all seeds from Barn
print("All persons in the Barn:")
for person in persons:
    print(person)

# Retrieving a specific seed by its key
george = persons.get("George")
print(george)

# Finding seeds based on criteria
results = persons.find_all(age=25)
# find_all() returns a Barn object populated \
# with the seeds that were found
print("Persons matching criteria (age 25):")
for person in results:
    print(person)

# Finding the first seed based on criteria
match_person = persons.find(name="Jim", age=25)

# Count seeds in the barn
count = len(persons)

# Get seed by index
first_person = persons[0]

# Get a Barn subset by slice
persons_subset = persons[1:3]

# Removing a seed from the Barn
persons.remove(match_person)
```

## What's The Purpose of an In-memory ORM

Barns offer ORM-like capabilities, allowing for easy storage, retrieval, and manipulation of objects (seeds) in memory without the overhead of a full database.

## Field Definitions

```Python
from databarn import Seed, Field, Barn

class Line(Seed):

    number: int = Field(key=True, auto=True)
        # type is int, so DataBarn will check it for validity
        # key => primary key [optional]
        # auto => Barn will assigned automatically with an incrementing number
    
    original: str = Field(frozen=True, none=False)
        # frozen=True => the value cannot be changed after assigned
        # none=False => the value cannot be None
    
    string: str = Field(default="Bla")
        # default => value to be automatically assigned when no value is provided
        # The default value is None by default

    note: bool | str = Field()
        # For multiple types, use the pipe operator

    processed = Field(unique=True)
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
lines = Barn(Line)

for content in text.split("\n"):
    line = Line(original=content, processed=content+" is at line: ")
    lines.append(line)
    # Once you have added it to Barn, the auto field will be assigned
    line.processed += str(line.number)
    print(line)
```

## Field Definition Constraints
1. `type annotation`: Assigning a value of a different type than the annotated for the field will raise a TypeError in Seed. More details in [Type Checking](#type-checking).
2. `auto=True`: Automatic incremental integer number. Altering the value of an auto field will raise an AttributeError.
3. `frozen=True`: Altering the value of a frozen field, after it has been assigned, will raise an AttributeError in Seed. It is mandatory to assign it when instantiating your Seed-derived class; otherwise, its value will be frozen to the default value.
4. `key=True`: Primary key.
    - Assigning None or a non-unique value to the key field will raise a AttributeError in Barn. After it has been appended to a Barn, the key value becomes immutable (frozen).
    - For a composite key, define more than one field as a key.
6. `none=False`: Assigning None value to the field will raise ValueError in Seed.
7. `unique=True`: Assigning a value that already exists for that field in the barn will raise a ValueError in Barn. None value is allowed for unique fields (but not for key fields).

## Type Checking
DataBarn relies on the [typeguard](https://github.com/agronholm/typeguard/) library, a runtime type checker, to check the types of values assigned to fields during code execution. It supports arbitrary type annotations (e.g., List[str], Dict[str, float], int, Union, etc.) for type checking. The following rules apply:
1. If the value doesn't match the type annotation, DataBarn will raise a TypeError.
2. None values are always accepted, regardless of the type annotation. If you want to enforce a non-None value, use `none=False` in the Field definition.
3. If the type annotation is a Union, the value must match at least one of the types in the Union.
4. If you don't define a type annotation, any value will be accepted.


# There's Only One Protected Name: `__dna__`
The only attribute name you cannot use in your Seed-model is `__dna__`. This approach was used to avoid polluting your namespace. All meta data and utillity methods are stored in the `__dna__` object.


## Accessing the Parent Via Child
For acessing the parent, use `child.__dna__.parent`. For instance:

```Python
# Children model
class Telephone(Seed):
    number: int = Field(key=True)

telephones = Barn(Telephone)

telephones.append(Telephone(number=1111111))
telephones.append(Telephone(number=2222222))

# Parent model
class User(Seed):
    name: str = Field(none=False)
    telephones: Barn = Field() # Use Barn-type to define a children field

kathryn = User(name="Kathryn", telephones=telephones)

telephone = kathryn.telephones[1]

parent = telephone.__dna__.parent

print("Parent is kathryn:", (parent is kathryn)) # outputs True
```

It also works with a single child:
```Python
# Single child model
class Passport(Seed):
    number: int = Field()

# Parent model
class Person(Seed):
    name: str = Field()
    passport: Passport = Field() # Use the child-class to define a single child field

person = Person(name="Michael", passport=Passport(99999))

# Access the corresponding parent Person
print(person.passport.__dna__.parent)
```

## Converting a Seed to a Dictionary
```Python
dikt = kathryn.__dna__.to_dict()
```
It's recursive, thus it will convert all children and any single child to dict as well.

## What If You Don't Define a Key?
In this case, Barn will use `Seed.__dna__.autoid` as the key, which is an auto-generated incremental integer number that starts at one.

```Python
from databarn import Seed, Field, Barn
from datetime import date

class Student(Seed):
    name: str = Field()
    phone: int = Field()
    enrolled: bool = Field()
    birthdate: date = Field()

student = Student(name="Rita", phone=12345678,
                  enrolled=True, birthdate=date(1998, 10, 27))

students = Barn(Student)
students.append(student)

# Accessing autoid
print(student.__dna__.autoid) # Outuputs 1

# The method `get()` will use the autoid value
student_1 = students.get(1)
print(student_1 is student) # Outputs True
```
