# Data Barn
**Data Barn** is a simple in-memory ORM and data carrier for Python.

# Dynamic Data Carrier

```Python
from databarn import Cob

my_obj = Cob(name="VPN", value=7, open=True)

print(my_obj.name, my_obj.value, my_obj.open)
```

## What's the Purpose of a Dynamic Data Carrier?

It's a quick way to create an object that stores named values, which is useful for passing data between functions. Instead of using a tuple with the values, you can name the values and access them through the Dot Notation (object.attribute). For example:

#### (Uncool) Tuple Solution

```Python

def get_anchor():
    ...
    return "www.example.com", False, "Bla"

# Too bad: You have to match the order, and deal with loose attributes
link, clickable, text = get_anchor()
```

#### (Cool) Dynamic Data Carrier Solution

```Python
from databarn import Cob, Barn

def get_anchor():
    ...
    return Cob(link="www.example.com", clickable=False, text="Bla")

# Now you've created an object that holds its descriptive attributes
anchor = get_anchor()
print(anchor)
print(anchor.clickable)
print(anchor.text)
print(anchor.link)

# If you have to handle multiple objects, you can store them in a Barn
anchors = Barn()
anchors.append(anchor) # More details below
```


# Static Data Carrier

```Python
from databarn import Cob, Field, Barn

class Person(Cob):
    name = Field(str, key=True) # Defining a key is optional
    age = Field(int)

# Instantiate it like this
person1 = Person(name="George", age=25)

# Or you can use positional arguments
person2 = Person("Bob", 31)
person3 = Person("Jim", 25)
```

# In-memory ORM

```Python
# To ensure consistency, pass your Cob-drived class \
# when creating a Barn instance.
persons = Barn(Person)

persons.append(person1)  # Barn stores in order
persons.append(person2)
persons.append(person3)

# Retrieving in order all cobs from Barn
print("All persons in the Barn:")
for person in persons:
    print(person)

# Retrieving a specific cob by its key
george = persons.get("George")
print(george)

# Finding cobs based on criteria
results = persons.find_all(age=25)
# find_all() returns a ResultsBarn() object populated \
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

# Removing a cob from the Barn
persons.remove(match_person)
```

## What's The Purpose of an In-memory ORM

Barn is intended to be a smart blend of a dictionary, list, SimpleNamespace and dataclass. It's a tool to manage multiple objects that have named attributes.

## Field Definitions

```Python
from databarn import Cob, Field, Barn

class Line(Cob):

    # Using a key is optional.
    # An auto field means that Barn will automatically \
    # assign an incremental integer number.
    number = Field(int, key=True, auto=True)

    # A frozen field cannot be modified after the value is assigned.
    # If `none` is false, you have to provide \
    # the value when instatiating it.
    original = Field(str, frozen=True, none=False)
    
    # If the type is not defined, any type will be accepted.
    processed = Field()
    
    # The default value is set to None, \
    # unless you define other value.
    string = Field(str, default="Bla")
    
    # For multiple types, use a tuple of types.
    note = Field(type=(bool, str)) # Or Field((bool, str))


text = """Aaaa
Bbbb
Cccc"""

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

1. `type`: Assigning a value of a different type than the defined field type will raise a TypeError in Cob. However, None is always accepted.
2. `auto=True`: Automatic incremental integer number. Altering the value of an auto field will raise an AttributeError.
3. `frozen=True`: Altering the value of a frozen field, after it has been assigned, will raise an AttributeError in Cob. It is mandatory to assign it when instantiating your Cob-derived class; otherwise, its value will be frozen to None.
4. `key=True`: Primary key.
    - Assigning None or a non-unique value to the key field will raise a ValueError in Barn. Nevertheless, the key value is *mutable*.
    - For a composite key, define more than one field as a key.
6. `none=False`: Setting None will raise ValueError in Cob.

## What If You Don't Define a Key?

In this case, Barn will use `Cob.__dna__.autoid` as the key, which is an auto-generated incremental integer number that starts at one.

```Python
from databarn import Cob, Field, Barn

class Student(Cob):
    name = Field(str)
    phone = Field(int)
    enrolled = Field(bool)

student = Student(name="Rita", phone=12345678, enrolled=True)

students = Barn(Student)
students.append(student)

# Accessing autoid
print(student.__dna__.autoid) # Outuputs 1

# The method `get()` will use the autoid value
cob = students.get(1)
print(cob is student) # Outputs True
```

## There's only one protected name: `__dna__`
The only attribute name you cannot use in your Cob model is `__dna__`. This approach was used to avoid polluting your namespace. All utillity methods and meta data are stored in the `__dna__` object.
