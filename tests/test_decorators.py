import pytest
from databarn.barn import Barn
from databarn.cob import Cob
from databarn.grain import Grain
from databarn.decorators import create_child_barn_grain, create_child_cob_grain
from databarn.exceptions import DataBarnSyntaxError


# --- Fixtures & Helper Classes ---

class SimpleCob(Cob):
    """A simple Cob model for testing."""
    name: str = Grain()
    value: int = Grain(default=0)


class Address(Cob):
    """A Cob model representing an address."""
    street: str = Grain()
    city: str = Grain()


class Person(Cob):
    """A Cob model representing a person."""
    name: str = Grain()
    age: int = Grain(default=0)


# --- Tests for create_child_barn_grain ---

class TestCreateChildBarnGrain:
    """Tests for the @create_child_barn_grain decorator."""

    def test_decorator_with_default_label(self):
        """Test that decorator generates label from class name."""
        @create_child_barn_grain()
        class Item(Cob):
            name: str = Grain()

        # Check that outer_model_grain was set
        assert Item.__dna__._outer_model_grain is not None
        grain = Item.__dna__._outer_model_grain
        
        # Label should be pluralized underscore version of class name
        assert grain.label == "items"
        assert grain.type == Barn
        assert grain.is_child_barn_ref is True

    def test_decorator_with_custom_label(self):
        """Test that decorator uses custom label when provided."""
        @create_child_barn_grain(label="custom_items")
        class Item(Cob):
            name: str = Grain()

        grain = Item.__dna__._outer_model_grain
        assert grain.label == "custom_items"

    def test_decorator_with_label_ending_in_s(self):
        """Test that decorator doesn't double-pluralize labels ending in 's'."""
        @create_child_barn_grain()
        class Address(Cob):
            street: str = Grain()

        grain = Address.__dna__._outer_model_grain
        # Should be "addresss" not "addressess" (no double-s added)
        assert grain.label == "address"

    def test_decorator_frozen_default(self):
        """Test that frozen parameter defaults to True."""
        @create_child_barn_grain()
        class Item(Cob):
            name: str = Grain()

        grain = Item.__dna__._outer_model_grain
        assert grain.frozen is True

    def test_decorator_frozen_false(self):
        """Test that frozen parameter can be set to False."""
        @create_child_barn_grain(frozen=False)
        class Item(Cob):
            name: str = Grain()

        grain = Item.__dna__._outer_model_grain
        assert grain.frozen is False

    def test_decorator_with_factory(self):
        """Test that decorator sets up factory for creating Barn instances."""
        @create_child_barn_grain()
        class Item(Cob):
            name: str = Grain()

        grain = Item.__dna__._outer_model_grain
        assert grain.factory is not None
        
        # Factory should create a Barn instance
        barn_instance = grain.factory()
        assert isinstance(barn_instance, Barn)
        assert barn_instance.model == Item

    def test_decorator_sets_child_model(self):
        """Test that decorator properly sets the child model reference."""
        @create_child_barn_grain()
        class Item(Cob):
            name: str = Grain()

        grain = Item.__dna__._outer_model_grain
        assert grain.child_model == Item

    def test_decorator_rejects_non_cob_class(self):
        """Test that decorator raises error if applied to non-Cob class."""
        with pytest.raises(DataBarnSyntaxError):
            @create_child_barn_grain()
            class NotACob:
                pass

    def test_decorator_with_grain_kwargs(self):
        """Test that additional grain kwargs are passed through."""
        @create_child_barn_grain(required=True, default=None)
        class Item(Cob):
            name: str = Grain()

        grain = Item.__dna__._outer_model_grain
        assert grain.required is True

    def test_decorator_in_outer_cob(self):
        """Test that decorated class can be used in outer Cob model."""
        @create_child_barn_grain()
        class Item(Cob):
            name: str = Grain()

        class Store(Cob):
            name: str = Grain()
            items: Barn = Item.__dna__._outer_model_grain  # Use the grain

        # Store should have the items grain
        store = Store(name="MyStore")
        # Check that items grain exists and is a Barn
        assert hasattr(store, "items")
        assert isinstance(store.items, Barn)
        assert store.items.model == Item

    def test_multiple_decorated_classes(self):
        """Test that multiple classes can be decorated independently."""
        @create_child_barn_grain()
        class Item(Cob):
            name: str = Grain()

        @create_child_barn_grain()
        class Order(Cob):
            id: int = Grain()

        item_grain = Item.__dna__._outer_model_grain
        order_grain = Order.__dna__._outer_model_grain

        assert item_grain.label == "items"
        assert order_grain.label == "orders"
        assert item_grain.child_model == Item
        assert order_grain.child_model == Order


# --- Tests for create_child_cob_grain ---

class TestCreateChildCobGrain:
    """Tests for the @create_child_cob_grain decorator."""

    def test_decorator_with_default_label(self):
        """Test that decorator generates label from class name."""
        @create_child_cob_grain()
        class HomeAddress(Cob):
            street: str = Grain()

        # Check that outer_model_grain was set
        assert HomeAddress.__dna__._outer_model_grain is not None
        grain = HomeAddress.__dna__._outer_model_grain
        
        # Label should be underscore version of class name (not pluralized)
        assert grain.label == "home_address"
        assert grain.type == HomeAddress
        assert grain.is_child_barn_ref is False

    def test_decorator_with_custom_label(self):
        """Test that decorator uses custom label when provided."""
        @create_child_cob_grain(label="address")
        class HomeAddress(Cob):
            street: str = Grain()

        grain = HomeAddress.__dna__._outer_model_grain
        assert grain.label == "address"

    def test_decorator_no_factory(self):
        """Test that decorator doesn't set factory for Cob grains."""
        @create_child_cob_grain()
        class HomeAddress(Cob):
            street: str = Grain()

        grain = HomeAddress.__dna__._outer_model_grain
        # For Cob grains, factory is not set (default is None)
        assert grain.factory is None

    def test_decorator_sets_child_model(self):
        """Test that decorator properly sets the child model reference."""
        @create_child_cob_grain()
        class HomeAddress(Cob):
            street: str = Grain()

        grain = HomeAddress.__dna__._outer_model_grain
        assert grain.child_model == HomeAddress
        assert grain.is_child_barn_ref is False

    def test_decorator_rejects_non_cob_class(self):
        """Test that decorator raises error if applied to non-Cob class."""
        with pytest.raises(DataBarnSyntaxError):
            @create_child_cob_grain()
            class NotACob:
                pass

    def test_decorator_with_grain_kwargs(self):
        """Test that additional grain kwargs are passed through."""
        @create_child_cob_grain(required=True)
        class HomeAddress(Cob):
            street: str = Grain()

        grain = HomeAddress.__dna__._outer_model_grain
        assert grain.required is True

    def test_decorator_in_outer_cob(self):
        """Test that decorated class can be used in outer Cob model."""
        @create_child_cob_grain()
        class HomeAddress(Cob):
            street: str = Grain()
            city: str = Grain()

        class Person(Cob):
            name: str = Grain()
            home_address: HomeAddress = HomeAddress.__dna__._outer_model_grain

        person = Person(name="John")
        # home_address should be None initially (no factory)
        assert hasattr(person, "home_address")
        assert person.home_address is None

    def test_decorator_can_set_cob_value(self):
        """Test that decorated Cob grain can be set with an instance."""
        @create_child_cob_grain()
        class HomeAddress(Cob):
            street: str = Grain()
            city: str = Grain()

        class Person(Cob):
            name: str = Grain()
            home_address: HomeAddress = HomeAddress.__dna__._outer_model_grain

        person = Person(name="John")
        address = HomeAddress(street="123 Main St", city="Springfield")
        person.home_address = address

        assert person.home_address == address
        assert person.home_address.street == "123 Main St"

    def test_multiple_decorated_classes(self):
        """Test that multiple classes can be decorated independently."""
        @create_child_cob_grain()
        class HomeAddress(Cob):
            street: str = Grain()

        @create_child_cob_grain()
        class WorkAddress(Cob):
            street: str = Grain()

        home_grain = HomeAddress.__dna__._outer_model_grain
        work_grain = WorkAddress.__dna__._outer_model_grain

        assert home_grain.label == "home_address"
        assert work_grain.label == "work_address"
        assert home_grain.child_model == HomeAddress
        assert work_grain.child_model == WorkAddress


# --- Integration Tests ---

class TestDecoratorIntegration:
    """Integration tests combining both decorators."""

    def test_nested_barn_and_cob(self):
        """Test using both decorators in a complex structure."""
        @create_child_barn_grain()
        class OrderItem(Cob):
            name: str = Grain()
            price: float = Grain()

        @create_child_cob_grain()
        class ShippingAddress(Cob):
            street: str = Grain()
            city: str = Grain()

        class Order(Cob):
            id: int = Grain()
            order_items: Barn = OrderItem.__dna__._outer_model_grain
            shipping_address: ShippingAddress = ShippingAddress.__dna__._outer_model_grain

        order = Order(id=1)
        
        # order_items should be a Barn instance
        assert isinstance(order.order_items, Barn)
        assert order.order_items.model == OrderItem
        
        # shipping_address should be None initially
        assert order.shipping_address is None
        
        # Add items to the barn
        item1 = OrderItem(name="Item1", price=10.0)
        order.order_items.add(item1)
        assert len(order.order_items) == 1
        
        # Set the shipping address
        address = ShippingAddress(street="456 Oak Ave", city="Shelbyville")
        order.shipping_address = address
        assert order.shipping_address.city == "Shelbyville"

    def test_class_name_variations(self):
        """Test label generation with various class name patterns."""
        @create_child_barn_grain()
        class User(Cob):
            name: str = Grain()

        @create_child_barn_grain()
        class UserProfile(Cob):
            bio: str = Grain()

        @create_child_barn_grain()
        class Address(Cob):
            street: str = Grain()

        user_grain = User.__dna__._outer_model_grain
        profile_grain = UserProfile.__dna__._outer_model_grain
        address_grain = Address.__dna__._outer_model_grain

        # Single char words get pluralized
        assert user_grain.label == "users"
        # Multi-word names get converted and pluralized
        assert profile_grain.label == "user_profiles"
        # Words already ending in 's' don't get double pluralized
        assert address_grain.label == "address"

    def test_decorator_inheritance(self):
        """Test that decorated models can be inherited."""
        @create_child_barn_grain()
        class BaseItem(Cob):
            name: str = Grain()

        # The grain is set on BaseItem, not inherited by ExtendedItem
        grain = BaseItem.__dna__._outer_model_grain
        assert grain is not None
        assert grain.child_model == BaseItem
        
        class ExtendedItem(BaseItem):
            description: str = Grain()
        
        # ExtendedItem extends BaseItem but doesn't have its own outer_model_grain
        # The decorator was only applied to BaseItem
        assert ExtendedItem.__dna__._outer_model_grain is None
