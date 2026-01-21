from knoxnotation.notation.parserlib import Parser

BASIC_HTML = "<!DOCTYPE html><html><head></head><body></body></html>"


def knox_to_html(knox_text):
    parser = Parser(knox_text, BASIC_HTML)
    return parser.convert()


def convert_knox_file_to_html_file(origin, dest="output.html"):
    with open(origin, "r") as file:
        string = file.read()
    html = knox_to_html(string)
    with open(dest, "w") as file:
        file.write(html)
    print(f"HTML saved to {dest}")


# if __name__ == "__main__":
#     # convert_knox_file_to_html_file("./docs/test4.knox")
#     convert_knox_file_to_html_file("./docs/Knox-Comprehensive-Syntax.knox")
