import re
from bs4 import MarkupResemblesLocatorWarning, BeautifulSoup
import warnings
from urlextract import URLExtract
from knoxnotation.common import trail
from databarn import Barn, Cob, Grain
from knoxnotation.notation import map

# Suppress specific BeautifulSoup warnings
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

UNLIKELY = "),#-;%^:&+}|}@}%}!}!}\\!}!#}!#}&!}!}!}[!/:;@?.$"


class Line(Cob):
    number: int = Grain(pk=True, auto=True)
    content: str = Grain(frozen=True)  # Original content
    string: str  # Processed string
    converted: bool = False


class Parser:

    def __init__(self, knox_text, html_base):
        self.lines = Barn(Line)
        for content in knox_text.split("\n"):
            line = Line(content=content, string=content)
            self.lines.append(line)

        self.soup = BeautifulSoup(html_base, "html.parser")

    def handle_code_block(self, line):
        if not line.string.startswith("```"):
            return False
        next_line = self.lines.get(line.number+1)
        language = line.string[3:].strip().lower()
        code_lines = []
        while True:
            if not next_line:
                return False
            if next_line.string.startswith("```"):
                line.converted = True
                next_line.converted = True
                pre_tag = trail.create_tag("pre")
                pre_tag.append(trail.create_tag("code"))
                if language:
                    pre_tag.code["language"] = language
                code_strings = []
                for code_line in code_lines:
                    code_strings.append(code_line.string)
                    code_line.converted = True
                pre_tag.code.append("\n".join(code_strings))
                self.soup.body.append(pre_tag)
                break
            code_lines.append(next_line)
            next_line = self.lines.get(next_line.number+1)
        return True

    def merge_strings_with_trailing_backslash(self, line):
        """Merge line strings ending with a backslash with the next line string."""
        next_line = self.lines.get(line.number+1)
        while line.string.endswith("\\") and next_line:
            line.string = line.string[:-1] + next_line.string
            next_line.string = None
            next_line.converted = True  # To skip
            next_line = self.lines.get(next_line.number+1)

    def handle_thematic_break(self, line):
        if line.string == map.ThematicBreak.MARKUP:
            self.soup.body.append(map.ThematicBreak.create_tag())
            line.converted = True
            return True
        return False

    def _break_down_anchors(self, string):
        extractor = URLExtract()

        # Extract URLs from the string
        urls = extractor.find_urls(string)

        anchors = Barn()

        for url in urls:
            # Check for URL within chevrons
            chevron_match = re.search(r'<([^>]+)>', string)
            if chevron_match:
                url = chevron_match.group(1)
                # Check if there's text within curly braces preceding the URL in chevrons
                curly_braces_match = re.search(
                    r'\{([^}]+)\}<' + re.escape(url) + '>', string)
                if curly_braces_match:
                    text = curly_braces_match.group(1)
                    finding = f"{{{text}}}<{url}>"
                else:
                    finding = f"<{url}>"
                    text = None
            else:
                puncts = (".", ",", ":", ";", "!", "?", ")", "]", "}")
                while url.endswith(puncts):
                    url = url[:-1]
                # Check for URL not in chevrons
                curly_braces_match = re.search(
                    r'\{([^}]+)\}' + re.escape(url), string)
                if curly_braces_match:
                    text = curly_braces_match.group(1)
                    finding = f"{{{text}}}" + url
                else:
                    finding = url
                    text = None
            anchor = Cob(finding=finding, url=url, text=text)
            anchors.append(anchor)
        return anchors

    def _replace_inline_code(self, string, replacement):
        matches = re.finditer(r"`(.*?)`", string)
        contents = []
        for match in matches:
            finding = match.group()
            content = match.group(1)
            string = string.replace(finding, replacement, 1)
            contents.append(content)
        return string, contents

    def _restore_and_format_code(self, string, to_replace, contents):
        for content in contents:
            # Use `string`, not `inner_html`
            html = str(trail.create_tag("code", string=content))
            string = string.replace(to_replace, html, 1)
        return string

    def format_inline(self, line):
        string, contents = self._replace_inline_code(line.string, UNLIKELY)

        # # Inline code
        # string = re.sub(r"`(.*?)`", r"<code>\1</code>", string)
        # Bold
        string = re.sub(r"\*(.*?)\*", r"<b>\1</b>",
                        string)
        # Emphasized
        string = re.sub(r"==(.*?)==", r"<em>\1</em>",
                        string)
        # Italic
        string = re.sub(r"=(.*?)=", r"<i>\1</i>",
                        string)
        # Underline
        string = re.sub(r"_(.*?)_", r"<u>\1</u>",
                        string)
        anchors = self._break_down_anchors(string)
        for anchor in anchors:
            if not anchor.text:
                anchor.text = anchor.url
            html = str(trail.create_tag("a", anchor.text, href=anchor.url))
            string = string.replace(anchor.finding, html)
        line.string = self._restore_and_format_code(string, UNLIKELY, contents)

    def _append_properly(self, line, tag):
        indent = len(line.string) - len(line.string.lstrip())
        if indent and self._has_valid_indent(line.string, 0) and self.soup.body.find_all():
            dest = self.soup.body.find_all(recursive=False)[-1]
        else:
            dest = tag
        dest.append(tag)

    def handle_heading(self, line):
        # heading_match = re.match(r"^(#+) (.*)", line.string)
        heading_match = map.Heading.PATTERN.match(line.string)
        if not heading_match:
            return False
        level = len(heading_match.group(1))
        content = heading_match.group(2)
        tag = trail.create_tag(f"h{level}", content)
        self.soup.body.append(tag)
        line.converted = True
        return True

    def handle_blockquote(self, line):
        if not line.string.startswith(map.QuoteBlock.get_markups()):
            return False
        markup = line.string[:len(map.QuoteBlock.MARKUP)]
        next_line = self.lines.get(line.number+1)
        blockquote_lines = []
        while next_line:
            if next_line.string.startswith(markup):
                line.converted = True
                next_line.converted = True
                main_tag = map.QuoteBlock.create_tag()
                for blockquote_line in blockquote_lines:
                    if len(blockquote_lines) > 1:
                        to_be_appended = trail.create_tag(
                            "p", blockquote_line.string)
                    else:
                        to_be_appended = blockquote_line.string
                    main_tag.blockquote.append(to_be_appended)
                    blockquote_line.converted = True

                # Attribution and Publication
                attrib_tag = main_tag.find(
                    class_=map.QuoteBlock.Attribution.KLASS)
                if (next_line := self.lines.get(next_line.number+1)) \
                        and next_line.string.startswith(map.QuoteBlock.Attribution.MARKUP):
                    next_line.converted = True
                    text = next_line.string[len(
                        map.QuoteBlock.Attribution.MARKUP):]
                    if map.QuoteBlock.Publication.MARKUP in text:
                        attribution, publication = text.split(
                            map.QuoteBlock.Publication.MARKUP, 1)
                    else:
                        attribution = text
                        publication = None
                    attribution = "&#8212 " + attribution  # &#8212 = long dash
                    # You can't use `append` here
                    attrib_tag.br.insert_before(
                        trail.html_to_soup(attribution))
                    pub_tag = main_tag.find(
                        class_=map.QuoteBlock.Publication.KLASS)
                    if publication is not None:
                        pub_tag.append(trail.html_to_soup(publication))
                    else:
                        # Delete publication tag
                        pub_tag.decompose()
                else:
                    # Delete attribution tag
                    attrib_tag.decompose()
                self.soup.body.append(main_tag)
                break
            blockquote_lines.append(next_line)
            next_line = self.lines.get(next_line.number+1)
        return True

    def _has_valid_indent(self, line, reference_indent=0):
        indent = len(line.string) - len(line.string.lstrip())
        diff_of_indent = indent - reference_indent
        extra_spaces = line.string[reference_indent:indent]
        # Only 2+ spaces are considered an indent. We recommend 4.
        # However, a single `/t` _is_ considered an indent, but not recommended.
        if diff_of_indent == 1 and extra_spaces == " ":
            if line.string.strip():
                msg = (f"Line {line.number} has one more initial space than the previous line."
                       "\nFor indentation, use at least 2 spaces; we recommend 4 spaces though.")
                # warnings.warn(msg, SyntaxWarning)
            return False
        return True

    def _guess_tag_name(self, string):
        lstripped = string.lstrip()
        if re.match(r"^\d+\. ", lstripped):
            return "ol"
        elif lstripped.startswith("- "):
            return "ul"
        return None

    def _break_down_list(self, line):
        tag_name = self._guess_tag_name(line.string)
        if not tag_name:
            return None
        lstripped = line.string.lstrip()
        indent = len(line.string) - len(lstripped)
        if tag_name == "ol":
            num = int(lstripped.split('.', 1)[0])
        else:
            num = None
        inner_html = lstripped.split(' ', 1)[1]
        return Cob(tag_name=tag_name, indent=indent, num=num, inner_html=inner_html)

    def _del_all_attrs(self, tag, attr):
        if tag.has_attr(attr):
            del tag[attr]
        for subtag in tag.find_all():
            if subtag.has_attr(attr):
                del subtag[attr]

    def _parse_list(self, line):
        litem = self._break_down_list(line)  # list item data
        main_tag = trail.create_tag(litem.tag_name, indent=litem.indent)
        last_list_tag = main_tag
        next_line = line
        first = True
        while next_line:
            litem = self._break_down_list(next_line)  # list item data

            if not litem:
                break

            item_tag = trail.create_tag("li", litem.inner_html)
            if litem.indent == main_tag["indent"]:  # Level 1
                # List type changed at level 1
                if litem.tag_name != main_tag.name:
                    break
                dest_tag = main_tag
                to_be_appended = item_tag
                last_list_tag = main_tag
            elif litem.indent == last_list_tag["indent"]:
                # List type changed at same level
                if litem.tag_name != last_list_tag.name:
                    break
                dest_tag = last_list_tag
                to_be_appended = item_tag
                # last_list_tag doesn't change
            elif litem.indent > last_list_tag["indent"]:
                nested_tag = trail.create_tag(
                    litem.tag_name, indent=litem.indent)
                if litem.tag_name == "ol" and litem.num != 1:
                    nested_tag["start"] = litem.num
                nested_tag.append(item_tag)
                if not self._has_valid_indent(line, last_list_tag["indent"]):
                    break
                dest_tag = last_list_tag.find_all("li", recursive=False)[-1]
                to_be_appended = nested_tag
                last_list_tag = nested_tag
            elif litem.indent < last_list_tag["indent"]:
                try:
                    item_parent = list(last_list_tag.parents)[-2]
                except IndexError:
                    msg = (f"The indentation of line {next_line.number} "
                           "was not found in the list.")
                    warnings.warn(msg, SyntaxWarning)
                    break
                # Find the parent list tag with the same indent
                if not (result := item_parent.find_all(indent=litem.indent)):
                    msg = (f"The indentation of line {next_line.number} "
                           "was not found in the list:")
                    # warnings.warn(msg, SyntaxWarning)
                    # Indentation not found in the same parent
                    break
                dest_tag = result[-1]
                if litem.tag_name != dest_tag.name:
                    # List type has changed when there was a previous same-indentation list
                    break
                to_be_appended = item_tag
                last_list_tag = dest_tag
            if first:
                if litem.tag_name == "ol" and litem.num != 1:
                    main_tag["start"] = litem.num
                first = False
            dest_tag.append(to_be_appended)
            next_line.converted = True
            next_line = self.lines.get(next_line.number+1)
        self._del_all_attrs(main_tag, "ident")
        return main_tag

    def handle_list(self, line):
        if self._guess_tag_name(line.string) and self._has_valid_indent(line, 0):
            tag = self._parse_list(line)
            self.soup.body.append(tag)
            return True
        return False

    def handle_headline(self, line):
        next_line = self.lines.get(line.number+1)
        tag = None
        if line.string and next_line and next_line.string:
            # it has be to be equal or larger than the lenght of the current line
            if len(next_line.string) >= len(line.string):
                if all(char == "=" for char in next_line.string):
                    tag = trail.create_tag("h1", line.string, klass="title")
                    # If <head> exists, but <title> wasn't created yet, then create a <title>
                    if self.soup.head and not self.soup.head.title:
                        title = trail.create_tag("title", tag.string)
                        self.soup.head.append(title)
                elif all(char == "-" for char in next_line.string):
                    tag = trail.create_tag("h2", line.string, klass="subtitle")
        if not tag:
            return False
        line.converted = True
        next_line.converted = True
        self.soup.body.append(tag)
        return True

    def handle_paragraph(self, line):
        dest_tag = self.soup.body
        to_be_appended = trail.create_tag("p", line.string)
        if line.string and self.soup.body.find_all():
            last_tag = self.soup.body.find_all(recursive=False)[-1]
            if last_tag.name == "p" and last_tag.get_text() and line.content != "\\":
                # If the the original line.content was a backslash,
                # then it's not a <br> case.
                last_tag.append(trail.create_tag("br"))
                to_be_appended = BeautifulSoup(line.string, "html.parser")
                dest_tag = last_tag
        line.converted = True
        dest_tag.append(to_be_appended)
        return True

    # def insert_knox_class(self):
    #     klass = "Knox"
    #     for tag in self.soup.find_all():
    #         if tag.name in ["head", "body"]:
    #             continue
    #         if "class" not in tag.attrs:
    #             tag["class"] = klass
    #         else:
    #             tag["class"].insert(0, klass)

    def convert(self):
        handle_funcs = [
            self.handle_heading,
            self.handle_thematic_break,
            self.handle_list,
            self.handle_blockquote,
            self.handle_headline,
            self.handle_paragraph,
        ]

        for line in self.lines:
            if line.converted:
                continue

            # handle_code_block is the very first check
            if self.handle_code_block(line):
                continue

            self.merge_strings_with_trailing_backslash(line)

            # handle_thematic_break has to come before the bold syntax (*)
            if self.handle_thematic_break(line):
                continue

            self.format_inline(line)

            for handle_func in handle_funcs:
                if handle_func(line):
                    break

        # self.insert_knox_class()
        return str(self.soup)
