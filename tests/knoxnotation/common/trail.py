import re
from typing import Callable
from bs4 import BeautifulSoup, Tag, MarkupResemblesLocatorWarning
import warnings



def create_tag(tag_name: str, inner_html: str = "",
               string: str = "", klass: str = "", **kwattrs) -> Tag:
    """Creates a BeautifulSoup tag using tag_name.

    Args:
        tag_name (str): E.g. "div"
        inner_html (str): E.g. "Text <b>inner html element</b> etc."
        string (str): Text with no html tags (cannot be used along with with `inner_html`)
        klass (str): E.g. "container"
        **kwattrs (str): Attributes other than class

    Return:
        tag: E.g. <div class='container'>Text <b>inner element</b> etc.</div>
    """
    if inner_html and string:
        raise ValueError(
            "It's not allowed to use both the `inner_html` and `string` arguments.")
    # Suppress specific BeautifulSoup warnings
    warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)
    soup = BeautifulSoup(inner_html, "html.parser")
    if klass:
        kwattrs["class"] = klass
    tag = soup.new_tag(tag_name, **kwattrs)
    if inner_html:
        tag.append(soup)
    if string:
        tag.append(string)
    return tag


def html_to_tag(html: str, strip_strings: bool = False):
    soup = BeautifulSoup(html, "html.parser")
    tag = soup.find()
    if strip_strings:
        for nav_string in list(tag.strings):
            nav_string.replace_with(nav_string.strip())
    return tag.extract()


def html_to_soup(html: str):
    return BeautifulSoup(html, "html.parser")
