import pytest

from databarn import Barn, Cob, one_to_many_grain, one_to_one_grain
from databarn.exceptions import DataBarnSyntaxError, DataValidationError
from databarn import Grain
from databarn.decorators import treat_before_assign, post_assign, config_cob


def test_one_to_many_grain_registers_child_metadata_and_factory() -> None:
    class Parent(Cob):
        title: str

        @one_to_many_grain("children", key="children_data")
        class Child(Cob):
            name: str

    grain = Parent.__dna__.get_grain("children")
    parent = Parent(title="family")
    created_barn = grain.factory()

    assert grain.parent_model is Parent
    assert grain.child_model is Parent.Child
    assert grain.is_child_barn is True
    assert isinstance(created_barn, Barn)
    assert created_barn.model is Parent.Child
    assert list(created_barn) == []
    assert Parent.Child.__dna__._outer_model_grain is grain
    assert isinstance(parent.children, Barn)
    assert list(parent.children) == []
    assert parent.__dna__.to_dict() == {"title": "family", "children_data": []}


def test_grain_factory_runs_after_provided_values_are_assigned() -> None:
    events: list[str] = []

    def build_nickname(_grain) -> str:
        events.append("factory")
        return "Ace"

    class Person(Cob):
        name: str
        nickname: str = Grain(factory=build_nickname)

        @treat_before_assign("name")
        def _record_name_assignment(self, value):
            events.append("name")
            return value

    person = Person(name="Ada")

    assert person.name == "Ada"
    assert person.nickname == "Ace"
    assert events == ["name", "factory"]


def test_one_to_one_grain_registers_child_metadata_and_forwards_kwargs() -> None:
    class Parent(Cob):

        @one_to_one_grain("profile", required=True, key="profile_data")
        class Profile(Cob):
            name: str

    grain = Parent.__dna__.get_grain("profile")
    parent = Parent(profile=Parent.Profile(name="Ada"))

    assert grain.parent_model is Parent
    assert grain.child_model is Parent.Profile
    assert grain.is_child_barn is False
    assert grain.factory is None
    assert grain.required is True
    assert grain.key == "profile_data"
    assert Parent.Profile.__dna__._outer_model_grain is grain
    assert parent.profile.name == "Ada"
    assert parent.__dna__.to_dict() == {"profile_data": {"name": "Ada"}}


def test_one_to_many_grain_rejects_dynamic_child_models() -> None:
    with pytest.raises(DataBarnSyntaxError):

        @one_to_many_grain("children")
        class Child(Cob):
            pass


def test_one_to_one_grain_rejects_dynamic_child_models() -> None:
    with pytest.raises(DataBarnSyntaxError):

        @one_to_one_grain("child")
        class Child(Cob):
            pass


def test_before_assign_preprocesses_value() -> None:
    class User(Cob):
        name: str = Grain()
        age: int = Grain()

        @treat_before_assign('name')
        def _normalize_name(self, value):
            return value.strip().title()

        @treat_before_assign('age')
        def _normalize_age(self, value):
            return int(value)

    u = User(name="  alice  ", age= "30")
    assert u.name == "Alice"
    assert u.age == 30

    u.name = "  bob  "
    assert u.name == "Bob"

    # ensure preprocessor for 'age' does not run on 'name'
    u.age = "40"
    assert u.age == 40


def test_before_assign_rejects_invalid_value() -> None:
    """Test that @treat_before_assign can raise DataValidationError to reject assignment."""
    class User(Cob):
        name: str = Grain()

        @treat_before_assign('name')
        def _check_name(self, value):
            if not isinstance(value, str) or not value.strip():
                raise DataValidationError("name must be a non-empty string")
            return value.strip()

    u = User()
    # valid assignment
    u.name = " Alice "
    assert u.name == "Alice"

    # invalid assignment should raise
    with pytest.raises(DataValidationError):
        u.name = "   "


def test_before_assign_mro_ordering() -> None:
    """Ensure multiple @treat_before_assign handlers on base and subclass run in MRO order."""
    class Base(Cob):
        name: str = Grain()

        @treat_before_assign('name')
        def _base(self, value):
            return value + "_B"

    class Sub(Base):
        @treat_before_assign('name')
        def _sub(self, value):
            return value + "_S"

    s = Sub()
    s.name = "v"
    # Sub._sub runs first, then Base._base, producing 'v_S_B'
    assert s.name == "v_S_B"


def test_post_assign_validates_after_assignment() -> None:
    """Test that @post_assign runs after assignment and can access the assigned value."""
    class User(Cob):
        email: str = Grain()

        @post_assign('email')
        def _validate_email(self):
            if '@' not in self.email:
                raise DataValidationError("Email must contain '@' symbol")

    u = User()
    # Valid email should pass
    u.email = "alice@example.com"
    assert u.email == "alice@example.com"

    # Invalid email should raise DataValidationError
    with pytest.raises(DataValidationError):
        u.email = "invalid-email"


def test_post_assign_propagates_errors() -> None:
    """Test that errors raised in @post_assign methods propagate and fail the assignment."""
    class Product(Cob):
        price: float = Grain()

        @post_assign('price')
        def _validate_price(self):
            if self.price <= 0:
                raise DataValidationError("Price must be positive")

    p = Product()
    # Valid price should succeed
    p.price = 99.99
    assert p.price == 99.99

    # Invalid price should raise and assignment should fail
    with pytest.raises(DataValidationError):
        p.price = -10.0


def test_post_assign_multiple_grains() -> None:
    """Test multiple @post_assign decorators on different grain labels."""
    class Account(Cob):
        username: str = Grain()
        password: str = Grain()

        @post_assign('username')
        def _validate_username(self):
            if len(self.username) < 3:
                raise DataValidationError("Username must be at least 3 characters")

        @post_assign('password')
        def _validate_password(self):
            if len(self.password) < 8:
                raise DataValidationError("Password must be at least 8 characters")

    acc = Account()

    # Valid username
    acc.username = "alice"
    assert acc.username == "alice"

    # Invalid username
    with pytest.raises(DataValidationError):
        acc.username = "ab"

    # Valid password
    acc.password = "secure_password_123"
    assert acc.password == "secure_password_123"

    # Invalid password
    with pytest.raises(DataValidationError):
        acc.password = "short"


def test_post_assign_with_before_assign() -> None:
    """Test that @treat_before_assign and @post_assign work together."""
    class Item(Cob):
        name: str = Grain()

        @treat_before_assign('name')
        def _normalize_name(self, value):
            # Preprocessor: normalize input
            return value.strip().title()

        @post_assign('name')
        def _validate_name(self):
            # Post-processor: validate normalized value
            if not self.name or self.name.isspace():
                raise DataValidationError("Name cannot be empty after normalization")

    item = Item()
    # Valid: preprocessor normalizes, post-processor accepts
    item.name = "  hello world  "
    assert item.name == "Hello World"

    # Invalid: preprocessor would normalize but post-processor would reject
    with pytest.raises(DataValidationError):
        item.name = "   "  # after normalization becomes empty


def test_post_assign_return_value_ignored() -> None:
    """Test that return value from @post_assign method is ignored."""
    class Counter(Cob):
        value: int = Grain()

        @post_assign('value')
        def _post_process(self):
            # Return value should be ignored
            return "This return value should be ignored"

    c = Counter()
    c.value = 42
    assert c.value == 42
    # No exception means test passed


def test_post_assign_only_called_for_matching_label() -> None:
    """Test that @post_assign only runs for its matching grain label."""
    class Data(Cob):
        field_a: str = Grain()
        field_b: str = Grain()
        call_count: int = 0

        @post_assign('field_a')
        def _validate_a(self):
            self.call_count += 1

    d = Data()
    d.field_a = "value_a"
    assert d.call_count == 1

    # Assigning to field_b should NOT trigger the post_assign for field_a
    d.field_b = "value_b"
    assert d.call_count == 1  # Should still be 1, not incremented


def test_config_cob_sets_blueprint() -> None:
    @config_cob("dynamic")
    class MyDynamicModel(Cob):
        x: int = 1

    assert MyDynamicModel.__dna__.blueprint == "dynamic"
    assert MyDynamicModel.__dna__.on_extra_kwargs == "create"


def test_config_cob_defaults_on_extra_kwargs_to_raise_for_static() -> None:
    @config_cob("static")
    class MyStaticModel(Cob):
        x: int = 1

    assert MyStaticModel.__dna__.blueprint == "static"
    assert MyStaticModel.__dna__.on_extra_kwargs == "raise"


def test_config_cob_on_extra_kwargs_create_requires_dynamic_blueprint() -> None:
    with pytest.raises(DataBarnSyntaxError) as exc_info:
        @config_cob(blueprint="static", on_extra_kwargs="create")
        class Person(Cob):
            name: str

    assert "on_extra_kwargs='create'" in str(exc_info.value)


def test_config_cob_on_extra_kwargs_create_rejects_static_after_inherited_dynamic() -> None:
    with pytest.raises(DataBarnSyntaxError) as exc_info:
        @config_cob(blueprint="static", on_extra_kwargs="create")
        class EmptyDynamic(Cob):
            pass

    assert "blueprint must be 'dynamic'" in str(exc_info.value)


def test_config_cob_on_extra_kwargs_create_with_dynamic_blueprint() -> None:
    @config_cob(blueprint="dynamic", on_extra_kwargs="create")
    class Hybrid(Cob):
        name: str

    h = Hybrid(name="Ada", score=99)
    assert h.name == "Ada"
    assert h.score == 99


def test_config_cob_on_extra_kwargs_ignore() -> None:
    @config_cob(on_extra_kwargs="ignore")
    class Person(Cob):
        name: str

    p = Person(name="Ada", age=99)
    assert p.name == "Ada"
    assert not hasattr(p, "age")


def test_config_cob_invalid_on_extra_kwargs() -> None:
    with pytest.raises(DataBarnSyntaxError) as exc_info:
        @config_cob(on_extra_kwargs="nope")
        class M(Cob):
            pass

    assert "Invalid on_extra_kwargs" in str(exc_info.value)


def test_config_cob_strict_unknown_kw_for_decorated_dynamic_model() -> None:
    @config_cob("dynamic", on_extra_kwargs="raise")
    class MyDynamicModel(Cob):
        x: int = 1

    with pytest.raises(DataValidationError):
        MyDynamicModel(x=1, unknown=2)


def test_config_cob_invalid_blueprint() -> None:
    with pytest.raises(DataBarnSyntaxError) as exc_info:
        @config_cob("invalid_blueprint")
        class MyModel(Cob):
            pass
    assert "Invalid blueprint 'invalid_blueprint'" in str(exc_info.value)


def test_config_cob_missing_dna() -> None:
    class MissingDnaModel(Cob):
        pass
    
    # Manually set __dna__ to None to simulate the error condition
    MissingDnaModel.__dna__ = None

    with pytest.raises(DataBarnSyntaxError) as exc_info:
        config_cob("static")(MissingDnaModel)
        
    assert "model DNA not initialized" in str(exc_info.value)

