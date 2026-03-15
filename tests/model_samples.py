from databarn import *


class Payload(Cob):
    model: str = Grain(required=True)
    temperature: float
    max_tokens: int
    reasoning_effort: str
    stream: bool = False

    @one_to_one_grain("response_format")
    class ResponseFormat(Cob):
        type: str = Grain("json_object")

    @one_to_many_grain('messages')
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

    @one_to_many_grain("messages")
    class Message(Cob):
        role: str = Grain(required=True)
        content: str = Grain(required=True)


class Person(Cob):
    address: str

    @one_to_one_grain("natural")
    class Natural(Cob):
        first_name: str = Grain(required=True)
        last_name: str = Grain(required=True)

    @one_to_one_grain("legal")
    class Legal(Cob):
        company_name: str = Grain(required=True)
        registration_number: str = Grain(required=True)


class LineWithAutoId(Cob):
    number: int = Grain(pk=True, autoenum=True)
    content: str = Grain(frozen=True, required=True)  # Original content
    string: str  # Processed string
    converted: bool = False


class LineWithAutoGrain(Cob):
    number: int = Grain(pk=True)
    content: str = Grain(frozen=True, required=True)  # Original content
    string: str  # Processed string
    converted: bool = False
    autoenum: int = Grain(autoenum=True)


class LineWithPostInit(Cob):
    number: int = Grain(pk=True, autoenum=True)
    content: str = Grain(frozen=True, required=True)  # Original content
    string: str  # Processed string

    def __post_init__(self):
        self.string = self.content.upper()


# class Product(Cob):
#     id: int = Grain(pk=True, autoenum=True)
#     name: str = Grain(required=True)


# class Client(Cob):
#     id: int = Grain(pk=True, autoenum=True)
#     name: str = Grain(required=True)


# class Order(Cob):
#     client: Client

#     @one_to_many_grain('order_products')
#     class OrderProduct(Cob):
#         product: Product = Grain(pk=True)
#         quantity: int = Grain(required=True)


# class Department(Cob):
#     name: str = Grain(pk=True)


# class Professor(Cob):
#     id: int = Grain(pk=True, autoenum=True)
#     name: str = Grain(required=True)
#     departments: Barn[Department]