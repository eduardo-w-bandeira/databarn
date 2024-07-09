# Data Barn
**Data Barn** is a simple in-memory ORM and data carrier, for Python.


# Using As a Data Carrier
## Example of Usage as a Data Carrier

```Python
from databarn import Model

anchor = Model(position=2.7, is_link=True, text="Bla")

print(anchor.position)
print(anchor.is_link)
print(anchor.text)
```

## What's the Purpose of a Data Carrier
A data carrier is a quick way to create an object that stores named values, which is useful for passing data between functions. Instead of using a tuple with the values, you can name the values and access them through obj.attr. This approach improves code readability by providing a Pythonic way to access values using descriptive field names instead of integer indices. For example:

```Python
from databarn import Model

# Using tuples
def solve_problem1():
    ...
    return (2.7, True, "Bla")

# With tuples, you have to use indices, match the order and deal with the names
position, is_link, text = solve_problem1()

# Data Barn data carrier makes that easier
def solve_problem2():
    ...
    return Model(position=2.7, is_link=True, text="Bla")

# Now you created an object that holds its descriptive attributes
anchor = solve_problem2()
print(anchor.position)
print(anchor.is_link)
print(anchor.text)
```

# Using As an ORM

## Example of Usage As an ORM

```Python
from databarn import Model, Field, Barn

class Person(Model):
    name = Field(str, primary_key=True) # Defining a primary key is optional
    age = Field(int)

# Instantiate it like this
person1 = Person(name="Alice", age=25)

# Or you can use positional arguments
person2 = Person("Bob", 31)

# Or add attributes later
person3 = Person()
person3.name = "Jim"
person3.age = 25
```

### Adding objects to the Barn
```Python
barn = Barn()

barn.add(person1)
barn.add(person2)
barn.add(person3)
```

### Working with Barn objects
```Python
# Retrieving all objects from the Barn
all_persons = barn.get_all()
print("All persons in the Barn:")
for person in all_persons:
    print(person)

# Retrieving a specific object by primary key
alice = barn.get("Alice")
print(alice)

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

Barn is intended to store and manage multiple objects. Instead of using a list or a dictionary of objects, Barn will simplify the process.