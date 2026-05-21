import json
import pytest

from databarn import (
    Cob, Grain, Barn,
    post_init, treat_before_assign, post_assign,
    one_to_one_grain, one_to_many_grain, DataValidationError,
)


def test_strongly_typed_model_example():
    class Payload(Cob):
        model: str = Grain(required=True)
        temperature: float
        max_tokens: int
        reasoning_effort: str
        stream: bool = False

        @one_to_one_grain("response_format")
        class ResponseFormat(Cob):
            type: str

        @one_to_many_grain('messages')
        class Message(Cob):
            role: str = Grain(required=True)
            content: str = Grain(required=True)

    payload = Payload(
        model="gpt-5.4-mini",
        temperature=0.2,
        max_tokens=256,
        reasoning_effort="low",
    )

    payload.response_format = Payload.ResponseFormat(type="json_object")

    payload.messages.add(Payload.Message(role="user", content="Write a short haiku."))
    payload.messages.add(
        Payload.Message(
            role="assistant",
            content="Quiet code unfolds\nIdeas bloom in typed silence\nLogic breathes in form",
        )
    )

    assert payload.response_format.type == "json_object"
    assert payload.model == "gpt-5.4-mini"
    assert payload["temperature"] == 0.2
    assert payload.stream is False
    assert payload.messages[0].role == "user"

    # to_dict / to_json roundtrip
    as_dict = payload._dna_.to_dict()
    as_json = payload._dna_.to_json()
    assert isinstance(as_dict, dict)
    assert json.loads(as_json)


def test_dynamic_model_quick_carrier():
    anchor = Cob(link="www.example.com", clickable=True, text="Bla")
    assert anchor.clickable is True
    assert anchor.text == "Bla"
    assert anchor.link == "www.example.com"


def test_static_model_verifying_constraints():
    class Connection(Cob):
        name: str
        value: int
        open: bool

    connection = Connection(name="VPN", value=7, open=True)
    assert "Connection(" in repr(connection)
    assert connection.name == "VPN"
    assert connection.value == 7
    assert connection.open is True


def test_create_cob_from_json_normalizes_keys():
    json_str = '''
    {
      "order-id": "ORD-2026-9941",
      "customer details": {
        "first-name": "Alex",
        "email": "alex@example.com",
        "global": true
      },
      "1st-time-buyer": true,
      "line-items": [
        {"sku": "SKU-442", "item price": 29.99, "quantity": 2},
        {"sku": "SKU-109", "item price": 14.50, "quantity": 1}
      ]
    }'''

    order = Cob._dna_.create_cob_from_json(json_str)

    assert order.order_id == "ORD-2026-9941"
    assert order.customer_details.first_name == "Alex"
    assert order.customer_details.global_ is True
    assert order.line_items[0].sku == "SKU-442"
    assert float(order.line_items[1].item_price) == 14.5
    assert order.customer_details.email == "alex@example.com"


def test_create_barn_from_csv_example():
    class Person(Cob):
        first_name: str
        last_name: str

    csv_str = "first name,last name\nAda,Lovelace\nGrace,Hopper\n"

    people = Person._dna_.create_barn_from_csv(csv_str)

    assert isinstance(people, Barn)
    assert len(people) == 2
    assert people[0].first_name == "Ada"
    assert people[1].last_name == "Hopper"


def test_post_init_decorator_runs_after_init():
    class Person(Cob):
        name: str
        license: int
        _inited: bool = False

        @post_init
        def init_person(self):
            self._inited = True

    p = Person(name="Alice", license=987)
    assert p._inited is True


def test_treat_before_assign_and_post_assign_behaviors():
    class Person(Cob):
        name: str = Grain(required=True)

        @treat_before_assign('name')
        def _clean_name(self, value):
            if not isinstance(value, str) or not value.strip():
                raise DataValidationError("name must be a non-empty string")
            return value.strip().title()

    p = Person(name="  alice  ")
    assert p.name == "Alice"

    with pytest.raises(DataValidationError):
        Person(name="   ")

    class Account(Cob):
        email: str = Grain(required=True)

        @post_assign('email')
        def _validate_email(self):
            if '@' not in self.email:
                raise DataValidationError("Email must contain '@' symbol")

    with pytest.raises(DataValidationError):
        Account(email="no-at-symbol")
