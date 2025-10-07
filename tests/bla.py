from databarn import *

class Payload(Cob):
    model: str = Grain(required=True)
    temperature: float = Grain()
    max_tokens: int = Grain()
    # reasoning_effort: str = Grain() # Reasoning effort is not supported in deepseek
    stream: bool = Grain(default=False)
    # response_format: Cob = Grain(default=Cob(type="json_object"))

    @create_child_cob_grain("response_format")
    class ResponseFormat(Cob):
        type: str = Grain("json_object")

    @create_child_barn_grain('messages')
    class Message(Cob):
        role: str = Grain(required=True)
        content: str = Grain(required=True)

class Person(Cob):
    address: str = Grain()

    @create_child_cob_grain("natural")
    class Natural(Cob):
        first_name: str = Grain(required=True)
        last_name: str = Grain(required=True)
    
    @create_child_cob_grain("legal")
    class Legal(Cob):
        company_name: str = Grain(required=True)
        registration_number: str = Grain(required=True)