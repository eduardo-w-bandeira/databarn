import pytest

from databarn import Cob, Grain, Barn, create_child_barn_grain, create_child_cob_grain
from databarn.exceptions import *

class Documentation(Cob):
    title: str = Grain(required=True)
    version: str = Grain(required=True)
    
    @create_child_cob_grain('metadata')
    class DocumentMetadata(Cob):
        author: str = Grain(required=True)
        created_at: str = Grain()
        last_modified: str = Grain()
        
        @create_child_barn_grain('contributors')
        class Contributor(Cob):
            name: str = Grain(required=True)
            role: str = Grain()
            email: str = Grain()
    
    @create_child_barn_grain('sections')
    class Section(Cob):
        title: str = Grain(required=True)
        content: str = Grain()
        order: int = Grain()
        
        @create_child_barn_grain('subsections')
        class Subsection(Cob):
            title: str = Grain(required=True)
            content: str = Grain()
            
            @create_child_cob_grain('code_example')
            class CodeExample(Cob):
                language: str = Grain(required=True)
                code: str = Grain(required=True)
                description: str = Grain()



class Payload(Cob):
    model: str = Grain(required=True)
    temperature: float = Grain()
    max_tokens: int = Grain()
    stream: bool = Grain(default=False)

    @create_child_cob_grain("response_format")
    class ResponseFormat(Cob):
        type: str = Grain("json_object")

    @create_child_barn_grain('messages')
    class Message(Cob):
        role: str = Grain(required=True)
        content: str = Grain(required=True)

def test_payload_model():
    with pytest.raises(GrainTypeMismatchError):
        payload = Payload(
            model=123,  # should be str
            temperature=0.7,
            max_tokens=150,
            stream=True,
            messages=[
                Payload.Message(role="user", content="Hello!"),
                Payload.Message(role="assistant", content="Hi there! How can I help you?")
            ],
            response_format=Payload.ResponseFormat(type="json_array")
        )
    
    payload = Payload(
        model="gpt-4",
        temperature=0.7,
        max_tokens=150,
        stream=True,
        response_format=Payload.ResponseFormat(type="json_array")
    )

    message = Payload.Message(role="user", content="Hello!")
    assert payload.messages.add(message) is payload.messages
    assert payload.messages.add(Payload.Message(role="assistant", content="Hi there! How can I help you?")) is payload.messages
    assert len(payload.messages) == 2
    assert payload.messages[0].role == "user"
    assert payload.messages[0].content == "Hello!"
    assert payload.messages[0] is message  # same instance
    assert payload.model == "gpt-4"
    assert payload.temperature == 0.7
    assert payload.max_tokens == 150
    assert payload.stream is True
    assert isinstance(payload.messages, Barn)
    assert len(payload.messages) == 2
    assert payload.messages[0].role == "user"
    assert payload.messages[0].content == "Hello!"
    assert payload.response_format.type == "json_array"


def test_create_child_barn_grain_auto_label_and_attributes():
    """create_child_barn_grain should auto-generate label, set Barn type, factory and frozen."""
    from databarn.decorators import create_child_barn_grain
    from databarn import Barn

    @create_child_barn_grain()
    class AutoLabelChild(Cob):
        foo: str = Grain()

    assert hasattr(AutoLabelChild.__dna__, '_outer_model_grain')
    grain = AutoLabelChild.__dna__._outer_model_grain
    # pascal_to_underscore(AutoLabelChild) -> auto_label_child -> pluralized
    assert grain.label == 'auto_label_childs'
    assert grain.type is Barn
    # factory should create a Barn for the child model
    barn = grain.factory()
    assert isinstance(barn, Barn)
    assert barn.model is AutoLabelChild
    # default frozen for create_child_barn_grain is True
    assert grain.frozen is True


def test_create_child_barn_grain_with_explicit_label_and_frozen_false():
    from databarn.decorators import create_child_barn_grain

    @create_child_barn_grain('my_items', frozen=False)
    class ExplicitChild(Cob):
        x: int = Grain()

    grain = ExplicitChild.__dna__._outer_model_grain
    assert grain.label == 'my_items'
    assert grain.frozen is False


def test_create_child_cob_grain_auto_and_explicit_label():
    from databarn.decorators import create_child_cob_grain

    @create_child_cob_grain()
    class AutoCob(Cob):
        a: str = Grain()

    grain = AutoCob.__dna__._outer_model_grain
    assert grain.label == 'auto_cob'
    # Type for cob grain should be the child model itself
    assert grain.type is AutoCob

    @create_child_cob_grain('profile')
    class ProfileChild(Cob):
        bio: str = Grain()

    grain2 = ProfileChild.__dna__._outer_model_grain
    assert grain2.label == 'profile'
    assert grain2.type is ProfileChild


def test_decorators_raise_on_non_cob():
    from databarn.decorators import create_child_barn_grain, create_child_cob_grain
    from databarn.exceptions import DataBarnSyntaxError

    with pytest.raises(DataBarnSyntaxError):
        @create_child_barn_grain()
        class NotACob:
            pass

    with pytest.raises(DataBarnSyntaxError):
        @create_child_cob_grain()
        class AlsoNotACob:
            pass


def test_documentation_nested_decorators_grains():
    """Verify nested create_child_barn_grain / create_child_cob_grain behavior
    using the `Documentation` class defined above.
    """
    from databarn import Barn

    # Top-level grains added to Documentation
    meta_grain = Documentation.__dna__.get_grain('metadata')
    assert meta_grain.label == 'metadata'
    assert meta_grain.type is Documentation.DocumentMetadata
    # The grain object assigned to the parent should be the same as the
    # _outer_model_grain stored on the nested class's __dna__
    assert meta_grain is Documentation.DocumentMetadata.__dna__._outer_model_grain

    sections_grain = Documentation.__dna__.get_grain('sections')
    assert sections_grain.label == 'sections'
    # create_child_barn_grain sets the grain type to Barn
    from databarn import Barn
    assert sections_grain.type is Barn

    # Contributor inside DocumentMetadata should be a Barn-type grain
    contrib_grain = Documentation.DocumentMetadata.__dna__.get_grain('contributors')
    assert contrib_grain.label == 'contributors'
    assert contrib_grain.type is Barn
    # default frozen for create_child_barn_grain is True
    assert contrib_grain.frozen is True
    # factory should create a Barn for the Contributor model
    barn = contrib_grain.factory()
    assert isinstance(barn, Barn)
    assert barn.model is Documentation.DocumentMetadata.Contributor


def test_instantiation_creates_barns_for_factory_grains():
    """When a Cob with Barn-type seeds is instantiated, the Barn factory
    should be called and the attribute set to a Barn instance.
    """
    from databarn import Barn

    # Documentation has top-level Barn 'sections' -> should be set on init
    doc = Documentation(title='Doc', version='1.0')
    assert isinstance(doc.sections, Barn)
    assert doc.sections.model is Documentation.Section

    # If we instantiate the nested DocumentMetadata, its 'contributors'
    # Barn should be created by its factory
    dm = Documentation.DocumentMetadata(author='Alice')
    assert isinstance(dm.contributors, Barn)
    assert dm.contributors.model is Documentation.DocumentMetadata.Contributor

    # Check deeper nesting: Subsection has a cob grain 'code_example'
    subsection_grain = Documentation.Section.Subsection.__dna__.get_grain('code_example')
    assert subsection_grain.label == 'code_example'
    assert subsection_grain.type is Documentation.Section.Subsection.CodeExample

