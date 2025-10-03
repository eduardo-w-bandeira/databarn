from databarn import Cob, Grain, wiz_create_child_barn, wiz_create_child_cob

class Payload(Cob):
    model: str = Grain(required=True)
    temperature: float = Grain()
    max_tokens: int = Grain()
    # reasoning_effort: str = Grain() # Reasoning effort is not supported in deepseek
    stream: bool = Grain(default=False)
    response_format: Cob = Grain(default=Cob(type="json_object"))

    @wiz_create_child_cob("response_format")
    class ResponseFormat(Cob):
        type: str = Grain("json_object")

    @wiz_create_child_barn('messages')
    class Message(Cob):
        role: str = Grain(required=True)
        content: str = Grain(required=True)

class Person(Cob):
    address: str = Grain()

    @wiz_create_child_cob("natural")
    class Natural(Cob):
        first_name: str = Grain(required=True)
        last_name: str = Grain(required=True)
    
    @wiz_create_child_cob("legal")
    class Legal(Cob):
        company_name: str = Grain(required=True)
        registration_number: str = Grain(required=True)