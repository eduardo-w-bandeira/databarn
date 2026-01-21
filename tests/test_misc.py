import sys
from pathlib import Path
import random
import datetime
import pytest
TESTS_DIR = Path(__file__).parent.resolve()  # noqa
from databarn import *
from knoxnotation import knoxtohtml

KNOX_FILE = TESTS_DIR / "knoxnotation" / "docs" / "Knox-Comprehensive-Syntax.knox"
with open(KNOX_FILE, "r") as file:
    KNOX_TEXT = file.read()

def test_real_world_app():
    expected_output = TESTS_DIR / "knoxnotation" / "expected-output.html"
    html = knoxtohtml.knox_to_html(KNOX_TEXT)
    with open(expected_output, "r") as file:
        expected_html = file.read()
    assert html == expected_html
    print(html)

class Line(Cob):
    number: int = Grain(pk=True)
    content: str = Grain(frozen=True, required=True)  # Original content
    string: str = Grain()  # Processed string
    converted: bool = Grain(default=False)
    auto: int = Grain(auto=True)


lines = Barn(Line)

for index, string in enumerate(KNOX_TEXT.split("\n")):
    line = Line(number=index+1, content=string, string=string)
    lines.append(line)


def test_cob_assignment():
    line = lines[random.randint(0, len(lines) - 1)]
    # Test type checking
    with pytest.raises(GrainTypeMismatchError):
        line.string = 123
    # Test frozen
    with pytest.raises(ConstraintViolationError):
        line.content = "abc"
    # Test required=True
    with pytest.raises(ConstraintViolationError):
        new_line = Line(number=1)
    # Test auto
    with pytest.raises(ConstraintViolationError):
        new_line = Line(content="abc")
        new_line.auto = 123
    # Test key change
    with pytest.raises(ConstraintViolationError):
        new_line = Line(number=len(lines) + 1, content="abc")
        lines.append(new_line)
        new_line.number = new_line.number + 1


def test_slice():
    subset = lines[20:30]
    assert len(subset) == 10


def test_auto_grain():
    class Line(Cob):
        number: int = Grain(auto=True)
    line1 = Line()
    line2 = Line()
    assert line1.number is None
    assert line2.number is None
    lines = Barn(Line)
    lines.append(line1)
    lines.append(line2)
    assert line1.number == 1
    assert line2.number == 2
    with pytest.raises(ConstraintViolationError):
        line1.number = 3


def test_auto_notnone_grain():
    class Line(Cob):
        number: int = Grain(auto=True, required=True)
    line1 = Line()
    line2 = Line()
    assert line1.number is None
    assert line2.number is None
    lines = Barn(Line)
    lines.append(line1)
    lines.append(line2)
    assert line1.number == 1
    assert line2.number == 2
    with pytest.raises(ConstraintViolationError):
        line1.number = 3


class Student(Cob):
    name: str = Grain()
    age: int = Grain(required=True)
    enrolled: bool = Grain(default=True)
    unique: str = Grain(unique=True)


def test_cob():
    student1 = Student(name="Rita", age=25, unique="a")
    student2 = Student(name="Bob", age=31, enrolled=False, unique="b")
    assert student1.name == "Rita"
    assert student1.age == 25
    assert student1.enrolled
    assert student2.name == "Bob"
    assert student2.age == 31
    assert not student2.enrolled


def test_barn():
    students = Barn(Student)
    students.append(Student(name="Rita", age=25, unique="a"))
    students.append(Student(name="Bob", age=31, enrolled=False, unique="b"))
    assert len(students) == 2
    assert students[0].name == "Rita"
    assert students[0].age == 25
    assert students[0].enrolled
    assert students[1].name == "Bob"
    assert students[1].age == 31
    assert not students[1].enrolled


def test_barn_find():
    students = Barn(Student)
    students.append(Student(name="Rita", age=25, unique="a"))
    students.append(Student(name="Bob", age=31, enrolled=False, unique="b"))
    results = students.find_all(name="Rita")
    assert len(results) == 1
    assert results[0].name == "Rita"


def test_barn_find_first():
    students = Barn(Student)
    students.append(Student(name="Rita", age=25, unique="a"))
    students.append(Student(name="Bob", age=31, enrolled=False, unique="b"))
    result = students.find(name="Rita")
    assert result.name == "Rita"


def test_barn_get():
    students = Barn(Student)
    students.append(Student(name="Rita", age=25, unique="a"))
    student = Student(name="Bob", age=31, enrolled=False, unique="b")
    id_ = id(student)
    students.append(student)
    result = students.get(id_)
    assert result.name == "Bob"


def test_barn_remove():
    students = Barn(Student)
    students.append(Student(name="Rita", age=25, unique="a"))
    students.append(Student(name="Bob", age=31, enrolled=False, unique="b"))
    students.remove(students[0])
    assert len(students) == 1


def test_unique():
    students = Barn(Student)
    students.append(Student(name="Rita", age=25, unique="a"))
    students.append(Student(name="Bob", age=31, enrolled=False, unique="b"))
    john = Student(name="John", age=25, unique="a")
    with pytest.raises(ValueError):
        students.append(john)
    john = Student(name="John", age=25, unique="a")
    john.unique = "c"
    students.append(john)
    rita = students.find(name="Rita")
    with pytest.raises(ValueError):
        rita.unique = "c"
    bob = students.find(name="Bob")
    with pytest.raises(ValueError):
        bob.unique = "a"


class Child(Cob):
    id: int = Grain(pk=True, auto=True)
    name: str = Grain()
    dob: datetime.date = Grain()


class Employee(Cob):
    id: int = Grain(pk=True, auto=True)
    name: str = Grain()
    dob: datetime.date = Grain()
    children: Barn = Grain()


mary = Employee(name="Mary", dob=datetime.date(
    1979, 12, 31))

mary_child1 = Child(name="Rita", dob=datetime.date(1990, 7, 27))
mary_child2 = Child(name="Bob", dob=datetime.date(1995, 8, 3))
mary_children = Barn(Child)
mary_children.append(mary_child1)
mary_children.append(mary_child2)
mary.children = mary_children

john = Employee(name="John", dob=datetime.date(1980, 5, 5))
john_child1 = Child(name="George", dob=datetime.date(2000, 5, 5))
john_children = Barn(Child)
john_children.append(john_child1)
john.children = john_children

janet = Employee(name="Janet", dob=datetime.date(1980, 5, 5))

employees = Barn(Employee)
employees.append(mary)
employees.append(john)
employees.append(janet)


def test_subbarn():
    print(employees[2])
    assert employees[1].children[0].name == "George"
    assert len(employees.get(1).children) == 2
    print(employees.get(1).__dna__.to_dict())
    print(employees.get(2).__dna__.to_dict())
    print(employees.get(3).__dna__.to_dict())
    assert type(employees.get(2).__dna__.to_dict()) is dict


def test_subbarn_parent():
    mary = employees.find(name="Mary")
    for subcob in mary.children:
        assert subcob.__dna__.parent == mary
    for subcob in john.children:
        assert subcob.__dna__.parent == john


class OneToOneChild(Cob):
    id: int = Grain(pk=True, auto=True)
    name: str = Grain()


class OneToOneParent(Cob):
    id: int = Grain(pk=True, auto=True)
    child: Cob = Grain(required=True)


def test_one_to_one():
    child = OneToOneChild(name="Kyle")
    parent = OneToOneParent(child=child)
    assert parent.child.name == "Kyle"
    assert parent.child.__dna__.parent is parent


def test_dynamic_one_to_one():
    dynamic_child = Cob(name="Kyle")
    parent = OneToOneParent(child=dynamic_child)
    assert parent.child.name == "Kyle"
    assert parent.child.__dna__.parent is parent


class Telephone(Cob):
    number: int = Grain(pk=True)

telephones = Barn(Telephone)

telephones.append(Telephone(number=12345678))
telephones.append(Telephone(number=87654321))

class User(Cob):
    name: str = Grain(required=True)
    telephones: Barn = Grain()

kathryn = User(name="Kathryn", telephones=telephones)

telephone = kathryn.telephones[1]

parent = telephone.__dna__.parent
print("Parent is kathryn:", (parent is kathryn))

class Passport(Cob):
    number: int = Grain()

class Person(Cob):
    name: str = Grain()
    passport: Passport = Grain()

person = Person(name="Michael", passport=Passport(99999))
