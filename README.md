# Data Barn
 Simple in-memory data manager and data carrier


# Example of Usage as a Data Carrier

A data carrier is a way to create an object that carries named values.
That's useful for passing data between functions.

```Python
from databarn import Model

anchor = Model(finding="<www.example.com>", url="http://www.example.com", text="This is an example")

print(anchor.finding)
print(anchor.url)
print(anchor.text)
```

# Example of Usage as a Data Manageer

```Python
from databarn import Model, Field, Barn

# Define a model class
class Person(Model):
    name = Field(str, primary_key=True) # Defining a primary key is optional
    age = Field(int)

# Create an instance of Barn
barn = Barn()

# Adding objects to the Barn
person1 = Person(name="Alice", age=30)
person2 = Person(name="Bob", age=25)

barn.add(person1)
barn.add(person2)

# Retrieving all objects from the Barn
all_persons = barn.get_all()
print("All persons in the Barn:")
for person in all_persons:
    print(person)

# Retrieving a specific object by primary key
alice = barn.get("Alice")
print("Retrieved person by primary key:")
print(alice)

# Finding objects based on criteria
criteria_match = barn.find_all(age=25)
print("Persons matching criteria (age 25):")
for person in criteria_match:
    print(person)

# Removing an object from the Barn
barn.remove(person2)
print("Remaining persons after removal:")
remaining_persons = barn.get_all()
for person in remaining_persons:
    print(person)

# Accessing attributes directly
print("Accessing attributes directly:")
print(f"Name of person1: {person1.name}")
print(f"Age of person1: {person1.age}")
```