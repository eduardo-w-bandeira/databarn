import re
from knoxnotation.common import trail


class _Base:

    @classmethod
    def create_tag(klass):
        return trail.html_to_tag(klass.HTML, True)

    @classmethod
    def get_markups(klass):
        var_name = "MARKUP"
        values = []
        for name in dir(klass):
            if name.startswith(var_name):
                remaining = name[len(var_name):]
                if remaining.isdigit() or not remaining:
                    values.append(getattr(klass, name))
        return tuple(values)


class QuoteBlock(_Base):
    MARKUP = '"""'
    MARKUP2 = "'''"
    KLASS = __qualname__

    class Attribution:
        MARKUP = "-- "
        KLASS = "Attribution"

    class Publication:
        MARKUP = " - "
        KLASS = "Publication"

    HTML = f"""
        <div class="{KLASS}">
            <blockquote></blockquote>
            <div class="{Attribution.KLASS}">
                <br/>
                <cite class="{Publication.KLASS}"></cite>
            </div>
        </div>"""


class ThematicBreak(_Base):
    MARKUP = "* * *"
    KLASS = __qualname__
    HTML = f"<hr class='{KLASS}'>"


class Heading(_Base):
    MARKUP = "#"
    PATTERN = re.compile(fr"^({MARKUP}+) (.*)")
    html = "<h{level}>"

    @classmethod
    def create_tag(klass, level):
        html = klass.html.format(level=level)
        return trail.html_to_tag(html)
