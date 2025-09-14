import re
from textwrap import dedent

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
    string = dedent(string).strip()
    string = string.replace("\n", " ")
    while "  " in string:
        string = string.replace("  ", " ")
    return string