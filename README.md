# Data Barn
**Data Barn** is a simple in-memory ORM and data carrier, for Python.

# Using Data Barn As a Data Carrier

```Python
from databarn import Model

obj = Model(name="VPN", value=7, open=True)

print(obj.name, obj.value, obj.open)
```

## What's the Purpose of a Data Carrier?

A data carrier is a quick way to create an object that stores named values, which is useful for passing data between functions. Instead of using a tuple with the values, you can name the values and access them through the "dot notation" (object.attribute). This approach improves code readability by providing a way to access values using descriptive field names instead of integer indices. For example:

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
from databarn import Model

def get_anchor():
    ...
    return Model(link="www.example.com", is_clickable=False, text="Bla")

# Now you've created an object that holds its descriptive attributes
anchor = get_anchor()
# Use meaningful object descriptions in any order
print(anchor.is_clickable)
print(anchor.text)
print(anchor.link)
```

# Using Data Barn As an In-memory ORM

```Python
from databarn import Model, Field, Barn

class Person(Model):
    name = Field(str, primary_key=True) # primary_key is optional
    age = Field(int)

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
all_persons = barn.get_all()
print("All persons in the Barn:")
for person in all_persons:
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
for person in barn.get_all():
    print(person)

# Accessing attributes directly
print("Accessing attributes directly:")
print(f"Name of person1: {person1.name}")
print(f"Age of person1: {person1.age}")
```

## What's The Purpose of an In-memory ORM

Barn is intended to be a smart alternative to lists, dictionaries, or even NamedTuple. It's a tool to manage multiple objects that have named attributes.

## Field Definitions

```Python
from databarn import Model, Field, Barn

class Line(Model):

    # Using a primary key is optional.
    # An autoincrement field means that Barn will automatically \
    # assign an incremental integer number.
    number = Field(int, primary_key=True, autoincrement=True)

    # A frozen field cannot be modified after the value is assigned.
    original = Field(str, frozen=True)
    
    # If the type is not defined, any type will be accepted.
    processed = Field()
    
    # The default value is set to None.
    # If a value is not provided when instantiating the field, \
    # the default value will be used.
    string = Field(str, default="Bla")
    
    # For multiple types, use a tuple of types.
    note = Field(type=(bool, str)) # Or just `Field((bool, str))`


barn = Barn()

text = """Aaaa
Bbbb
Cccc"""

for content in text.split("\n"):
    line = Line(original=content, processed=content+" is at line: ")
    barn.add(line)
    # Once you have added it to Barn, the autoincrement field will be assigned
    line.processed += str(line.number)
    print(line)
```

## Field Definition Constraints

1. TYPE: Assigning a value of a different type than the defined field type will raise a `TypeError`. However, `None` is always accepted.
2. AUTOINCREMENT: Altering the value of an autoincrement field will raise an `AttributeError`.
3. FROZEN: Altering the value of a frozen field, after it has been assigned, will raise an `AttributeError`. It is mandatory to assign it when instantiating your Model; otherwise, its value will be frozen to `None`.
4. PRIMARY KEY: Assigning `None` or a non-unique value to the primary key field will raise a `ValueError`. Nevertheless, the primary key value is *mutable*.
5. PRIMARY KEY: Defining multiple primary keys will raise a `ValueError`.

## What If You Don't Define a Primary Key?

In this case, Barn will use `auto_id` as the primary key, which is an auto-generated incremental integer number that starts at one.

```Python
from databarn import Model, Field, Barn

class Student(Model):
    name = Field(str)
    phone = Field(int)
    enrolled = Field(bool)

student = Student(name="Rita", phone=12345678, enrolled=True)

barn = Barn()
barn.add(student)

# Accessing auto_id
print(student._meta.auto_id) # Outuputs 1

# The method `get()` will use the auto_id value
obj = barn.get(1)
print(obj is student) # Outputs True
```

## Accessing Meta Data

```Python
# Using the last example as basis:
print(student._meta.name_field) # Outputs a dictionary containing each field_name and its field_instance.
print(student._meta.auto_id) # Outputs the auto-generated incremental integer id (even if not used).
print(student._meta.barn) # Outputs the Barn where the object is stored.
print(student._meta.pk_name) # Outputs either the primary key attribute name or None (if not provided).
print(student._meta.pk_value) # Outputs the primary key value (which may be user-defined or `auto_id`).

```

After being removed from the Barn, `auto_id` and `barn` will be rolled back to None. For example:
```Python
barn.remove(student)
print(student._meta.auto_id) # Outputs None
print(student._meta.barn) # Outputs None
```