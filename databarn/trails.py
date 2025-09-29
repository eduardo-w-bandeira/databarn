import re


class Sentinel:
    """A unique sentinel object to detect missing values."""

    def __repr__(self):
        return "<Sentinel>"
    
sentinel = Sentinel()

def pascal_to_underscore(name: str) -> str:
    """Converts a PascalCase name to underscore_case.
    Args:
        name (str): The PascalCase name to convert.
    Returns:
        str: The converted underscore_case name.
    """
    # Insert underscore before each capital letter (except the first one)
    # and convert the entire string to lowercase
    underscore = re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()
    return underscore


def fo(string: str):
    """Dedents and strips a multi-line string.

    Args:
        string (str): The multi-line string to format.

    Returns:
        str: The formatted string.
    """
    string = string.replace("\n", " ").strip()
    new_str = ""
    for char in string:
        if char.isspace():
            char = " "
        new_str += char
    while "  " in new_str:
        new_str = new_str.replace("  ", " ")
    return new_str


class dual_property:
    def __init__(self, method=None):
        self.method = method

    def __get__(self, ob, owner):
        if ob is None:
            # Class access
            return self.method(owner)
        # Instance access
        return self.method(ob)


class dual_method:
    def __init__(self, method):
        self.method = method

    def __get__(self, ob, owner):
        def wrapper(*args, **kwargs):
            abstraction = owner if ob is None else ob
            return self.method(abstraction, *args, **kwargs)
        return wrapper

# class class_property(property):
#     """A decorator that behaves like @property but for classmethods.
#     Usage:
#         class MyClass:
#             _value = 42

#             @class_property
#             def value(cls):
#                 return cls._value
#     """

#     def __get__(self, ob, klass):
#         return self.fget(klass)
