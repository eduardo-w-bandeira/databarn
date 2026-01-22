import pytest
from model_samples import (
	Payload,
	PayloadWithDynamiChildCob,
	Person,
	LineWithAutoId,
	LineWithAutoGrain,
	LineWithPostInit,
)
from databarn import *


def test_payload_child_cob_and_barn_behaviors():
	# Required 'model' must be provided
	with pytest.raises(ConstraintViolationError):
		Payload()

	payload = Payload(model="gpt-test")
	# Child cob grain initially None; can be set to child model
	assert payload.response_format is None
	payload.response_format = Payload.ResponseFormat()
	assert isinstance(payload.response_format, Payload.ResponseFormat)
	assert payload.response_format.type == "json_object"
	# Parent link is set on child cob
	assert payload.response_format.__dna__.parent is payload

	# Child barn grain auto-created and attached
	assert isinstance(payload.messages, Barn)
	# Add valid child cobs to barn
	m1 = Payload.Message(role="user", content="Hello")
	m2 = Payload.Message(role="assistant", content="Hi there")
	payload.messages.add(m1).add(m2)
	assert len(payload.messages) == 2
	# Parent link is set on child barn items
	assert m1.__dna__.parent is payload
	assert m2.__dna__.parent is payload

	# Missing required fields in child should raise
	with pytest.raises(ConstraintViolationError):
		Payload.Message(role=None, content="X")


def test_payload_with_dynamic_child_cob_default_and_parent():
	# This model defines a dynamic child cob as default value
	p = PayloadWithDynamiChildCob(model="gpt-test")
	assert isinstance(p.response_format, Cob)
	assert p.response_format.type == "json_object"
	# Parent link is set for the default child cob
	assert p.response_format.__dna__.parent is p


def test_person_child_cobs_auto_labels():
	p = Person(address="123 Street")
	# Explicitly labeled child cob
	p.natural = Person.Natural(first_name="John", last_name="Doe")
	assert p.natural.first_name == "John"
	# Auto-named child cob label from class name
	p.legal = Person.Legal(company_name="ACME", registration_number="REG-123")
	assert hasattr(p, "legal")
	assert isinstance(p.legal, Person.Legal)
	# Parent links
	assert p.natural.__dna__.parent is p
	assert p.legal.__dna__.parent is p


def test_line_with_autoid_barn_auto_assignment_and_frozen():
	# Manually assigning auto pk should fail
	with pytest.raises(ConstraintViolationError):
		LineWithAutoId(number=99, content="X")

	barn = LineWithAutoId.__dna__.create_barn()
	l1 = LineWithAutoId(content="abc")
	l2 = LineWithAutoId(content="def")
	barn.add(l1).add(l2)
	assert l1.number == 1
	assert l2.number == 2
	# Frozen content cannot be reassigned
	with pytest.raises(ConstraintViolationError):
		l1.content = "changed"


def test_line_with_auto_grain_assignment_via_barn():
	l = LineWithAutoGrain(number=10, content="xyz")
	# Manual assignment to auto grain should fail
	with pytest.raises(ConstraintViolationError):
		l.auto = 5
	# Barn sets auto when added
	barn = LineWithAutoGrain.__dna__.create_barn()
	barn.add(l)
	assert l.auto == 1


def test_line_with_post_init_sets_string_uppercase():
	l = LineWithPostInit(content="hello")
	assert l.string == "HELLO"


def test_to_dict_nested_conversion_for_payload():
	payload = Payload(model="gpt-nested")
	payload.response_format = Payload.ResponseFormat()
	payload.messages.add(Payload.Message(role="user", content="Hi"))
	payload.messages.add(Payload.Message(role="assistant", content="Hello"))

	d = payload.__dna__.to_dict()
	assert d["model"] == "gpt-nested"
	assert isinstance(d["response_format"], dict)
	assert d["response_format"]["type"] == "json_object"
	assert isinstance(d["messages"], list)
	assert d["messages"][0]["role"] == "user"
	assert d["messages"][1]["role"] == "assistant"
