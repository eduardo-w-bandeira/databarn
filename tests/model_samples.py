from databarn import *


class Payload(Cob):
    model: str = Grain(required=True)
    temperature: float
    max_tokens: int
    reasoning_effort: str
    stream: bool = False

    @create_child_cob_grain("response_format")
    class ResponseFormat(Cob):
        type: str = Grain("json_object")

    @create_child_barn_grain('messages')
    class Message(Cob):
        role: str = Grain(required=True)
        content: str = Grain(required=True)


class PayloadWithDynamiChildCob(Cob):
    model: str = Grain(required=True)
    temperature: float
    max_tokens: int
    reasoning_effort: str
    stream: bool = False
    response_format: Cob = Cob(type="json_object")  # Dynamic child cob grain

    @create_child_barn_grain()  # No name provided, to test auto-naming
    class Message(Cob):
        role: str = Grain(required=True)
        content: str = Grain(required=True)


class Person(Cob):
    address: str

    @create_child_cob_grain("natural")
    class Natural(Cob):
        first_name: str = Grain(required=True)
        last_name: str = Grain(required=True)

    @create_child_cob_grain()  # No name provided, to test auto-naming
    class Legal(Cob):
        company_name: str = Grain(required=True)
        registration_number: str = Grain(required=True)


class LineWithAutoId(Cob):
    number: int = Grain(pk=True, auto=True)
    content: str = Grain(frozen=True, required=True)  # Original content
    string: str  # Processed string
    converted: bool = False


class LineWithAutoGrain(Cob):
    number: int = Grain(pk=True)
    content: str = Grain(frozen=True, required=True)  # Original content
    string: str  # Processed string
    converted: bool = False
    auto: int = Grain(auto=True)


class LineWithPostInit(Cob):
    number: int = Grain(pk=True, auto=True)
    content: str = Grain(frozen=True, required=True)  # Original content
    string: str  # Processed string

    def __post_init__(self):
        self.string = self.content.upper()
