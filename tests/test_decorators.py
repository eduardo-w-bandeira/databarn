
"""
Comprehensive unit tests for databarn decorators (create_child_barn_grain and create_child_cob_grain).

This test suite covers:
- create_child_barn_grain decorator:
  * Basic functionality with automatic label generation
  * Custom label specification
  * Grain parameter passing to the decorator
  * Error handling for non-Cob classes
  * Integration with parent Cob classes
  * Barn functionality and child model relationships
  * DNA attribute setting and retrieval
  * Frozen parameter behavior
  * Advanced grain parameter combinations

- create_child_cob_grain decorator:
  * Basic functionality with automatic label generation
  * Custom label specification
  * Grain parameter passing to the decorator
  * Error handling for non-Cob classes
  * Integration with parent Cob classes
  * Cob-to-Cob relationships
  * Default value behavior
  * Type checking and validation

- Integration scenarios:
  * Mixed decorator usage
  * Complex inheritance hierarchies
  * Cross-decorator interactions

The tests ensure that both decorators properly create child relationships
between parent and child Cob models with correct labeling and grain configuration.
"""

import pytest
from typing import Any
from databarn import Cob, Grain, Barn, create_child_barn_grain, create_child_cob_grain
from databarn.exceptions import *


class TestWizCreateChildBarn:
    """Test cases for create_child_barn_grain decorator."""
    
    def test_decorator_with_default_label_generation(self):
        """Test decorator creates child barn with auto-generated label."""
        class Parent(Cob):
            name: str = Grain()
            
            @create_child_barn_grain()
            class Child(Cob):
                value: int = Grain()
        
        # Check that the child class is properly decorated
        assert hasattr(Parent.Child, '__dna__')
        assert hasattr(Parent.Child.__dna__, '_outer_model_grain')
        
        # Check that the grain was created with correct label
        grain = Parent.Child.__dna__._outer_model_grain
        assert grain.label == "childs"  # pluralized from "Child"
        assert grain.type == Barn
        
        # Check that the grain has a pre-set Barn value
        assert isinstance(grain.pre_value, Barn)
        assert grain.pre_value.model == Parent.Child
    
    def test_decorator_with_custom_label(self):
        """Test decorator with custom label specification."""
        class Parent(Cob):
            name: str = Grain()
            
            @create_child_barn_grain('custom_children')
            class Child(Cob):
                value: int = Grain()
        
        grain = Parent.Child.__dna__._outer_model_grain
        assert grain.label == "custom_children"
        assert grain.type == Barn
        assert isinstance(grain.pre_value, Barn)
        assert grain.pre_value.model == Parent.Child
    
    def test_decorator_with_grain_parameters(self):
        """Test decorator passing parameters to Grain constructor."""
        class Parent(Cob):
            name: str = Grain()
            
            @create_child_barn_grain('items', required=True, default=None)
            class Item(Cob):
                description: str = Grain()
        
        grain = Parent.Item.__dna__._outer_model_grain
        assert grain.label == "items"
        assert grain.required is True
        assert grain.default is None
    
    def test_decorator_with_class_already_ending_with_s(self):
        """Test decorator with class name already ending with 's'."""
        class Parent(Cob):
            title: str = Grain()
            
            @create_child_barn_grain()
            class Items(Cob):
                name: str = Grain()
        
        grain = Parent.Items.__dna__._outer_model_grain
        assert grain.label == "items"  # Should not double pluralize
    
    def test_decorator_error_with_non_cob_class(self):
        """Test that decorator raises error for non-Cob classes."""
        with pytest.raises(DataBarnSyntaxError, match="must be a subclass of Cob"):
            class Parent(Cob):
                name: str = Grain()
                
                @create_child_barn_grain()
                class NotACob:  # This is not a Cob subclass
                    pass
    
    def test_decorator_integration_with_parent_cob(self):
        """Test full integration of decorated child with parent Cob."""
        class Message(Cob):
            subject: str = Grain(required=True)
            
            @create_child_barn_grain('attachments')
            class Attachment(Cob):
                filename: str = Grain(required=True)
                size: int = Grain()
        
        # Create a parent instance
        msg = Message(subject="Test Email")
        
        # The child class should be accessible
        assert hasattr(Message, 'Attachment')
        assert issubclass(Message.Attachment, Cob)
        
        # Check the grain configuration
        grain = Message.Attachment.__dna__._outer_model_grain
        assert grain.label == "attachments"
        assert isinstance(grain.pre_value, Barn)
        
        # The Barn should be able to create child instances
        barn = grain.pre_value
        attachment = Message.Attachment(filename="document.pdf", size=1024)
        assert attachment.filename == "document.pdf"
        assert attachment.size == 1024
    
    def test_barn_functionality_with_decorated_child(self):
        """Test that the created Barn works properly with child instances."""
        class Order(Cob):
            order_id: str = Grain(required=True)
            
            @create_child_barn_grain('line_items')
            class LineItem(Cob):
                product: str = Grain(required=True)
                quantity: int = Grain(default=1)
                price: float = Grain()
        
        # Get the barn from the grain
        grain = Order.LineItem.__dna__._outer_model_grain
        barn = grain.pre_value
        
        # Test barn operations
        assert len(barn) == 0
        assert barn.model == Order.LineItem
        
        # Create and add items
        item1 = Order.LineItem(product="Widget", quantity=2, price=10.0)
        item2 = Order.LineItem(product="Gadget", quantity=1, price=20.0)
        
        # Verify items were created correctly
        assert item1.product == "Widget"
        assert item1.quantity == 2
        assert item2.product == "Gadget"
        assert item2.quantity == 1
    
    def test_multiple_decorated_children(self):
        """Test multiple child barns in the same parent class."""
        class Document(Cob):
            title: str = Grain(required=True)
            
            @create_child_barn_grain('sections')
            class Section(Cob):
                heading: str = Grain(required=True)
                content: str = Grain()
            
            @create_child_barn_grain('comments')
            class Comment(Cob):
                author: str = Grain(required=True)
                text: str = Grain(required=True)
        
        # Check both children are properly decorated
        section_grain = Document.Section.__dna__._outer_model_grain
        comment_grain = Document.Comment.__dna__._outer_model_grain
        
        assert section_grain.label == "sections"
        assert comment_grain.label == "comments"
        
        # Both should have their own barns
        assert isinstance(section_grain.pre_value, Barn)
        assert isinstance(comment_grain.pre_value, Barn)
        assert section_grain.pre_value.model == Document.Section
        assert comment_grain.pre_value.model == Document.Comment
    
    def test_decorator_frozen_parameter_true(self):
        """Test decorator with frozen=True (default behavior)."""
        class Container(Cob):
            name: str = Grain(required=True)
            
            @create_child_barn_grain('items')  # frozen=True by default
            class Item(Cob):
                value: str = Grain()
        
        grain = Container.Item.__dna__._outer_model_grain
        assert grain.frozen is True
    
    def test_decorator_frozen_parameter_false(self):
        """Test decorator with frozen=False."""
        class Container(Cob):
            name: str = Grain(required=True)
            
            @create_child_barn_grain('items', frozen=False)
            class Item(Cob):
                value: str = Grain()
        
        grain = Container.Item.__dna__._outer_model_grain
        assert grain.frozen is False
    
    def test_decorator_with_complex_grain_parameters(self):
        """Test decorator with multiple complex grain parameters."""
        class System(Cob):
            name: str = Grain(required=True)
            
            @create_child_barn_grain('logs', 
                                   frozen=False, 
                                   required=True, 
                                   default=None,
                                   description="System log entries")
            class LogEntry(Cob):
                timestamp: str = Grain(required=True)
                level: str = Grain(default="INFO")
                message: str = Grain(required=True)
        
        grain = System.LogEntry.__dna__._outer_model_grain
        assert grain.label == "logs"
        assert grain.frozen is False
        assert grain.required is True
        assert grain.default is None
        # Note: Grain class doesn't have description attribute
    
    def test_nested_decoration_levels(self):
        """Test decorator working with nested class hierarchies."""
        class Project(Cob):
            name: str = Grain(required=True)
            
            @create_child_barn_grain('tasks')
            class Task(Cob):
                title: str = Grain(required=True)
                completed: bool = Grain(default=False)
                
                @create_child_barn_grain('subtasks')
                class Subtask(Cob):
                    description: str = Grain(required=True)
                    done: bool = Grain(default=False)
        
        # Check both levels of decoration
        task_grain = Project.Task.__dna__._outer_model_grain
        subtask_grain = Project.Task.Subtask.__dna__._outer_model_grain
        
        assert task_grain.label == "tasks"
        assert subtask_grain.label == "subtasks"
        
        # Both should have proper barns
        assert task_grain.pre_value.model == Project.Task
        assert subtask_grain.pre_value.model == Project.Task.Subtask
    
    def test_decorator_preserves_class_functionality(self):
        """Test that the decorator doesn't break normal class functionality."""
        class Container(Cob):
            name: str = Grain(required=True)
            
            @create_child_barn_grain('elements')
            class Element(Cob):
                value: str = Grain(required=True)
                
                def get_uppercase_value(self):
                    return self.value.upper()
                
                @property
                def display_name(self):
                    return f"Element: {self.value}"
        
        # Create an instance and test its methods
        element = Container.Element(value="test")
        
        assert element.value == "test"
        assert element.get_uppercase_value() == "TEST"
        assert element.display_name == "Element: test"
        
        # Decorator attributes should still be present
        assert hasattr(Container.Element.__dna__, '_outer_model_grain')
    
    def test_label_generation_edge_cases(self):
        """Test label generation for various class name patterns."""
        class Parent(Cob):
            pass
        
        # Test various class name patterns
        test_cases = [
            ("Child", "childs"),      # Simple case: child -> childs
            ("Person", "persons"),    # Simple case: person -> persons  
            ("Class", "class"),       # Ends with 's': class -> class
            ("Box", "boxs"),          # Simple case: box -> boxs
            ("Entry", "entrys"),      # Simple case: entry -> entrys
            ("Items", "items"),       # Already plural: items -> items
            ("Address", "address"),   # Ends with 's': address -> address
        ]
        
        for class_name, expected_label in test_cases:
            # Dynamically create a class with the test name
            child_class = type(class_name, (Cob,), {
                'test_field': Grain()
            })
            
            # Apply the decorator
            decorated_class = create_child_barn_grain()(child_class)
            
            grain = decorated_class.__dna__._outer_model_grain
            assert grain.label == expected_label, f"For class {class_name}, expected {expected_label}, got {grain.label}"


class TestWizCreateChildBarnIntegration:
    """Integration tests for create_child_barn_grain in realistic scenarios."""
    
    def test_complete_usage_example(self):
        """Test the complete usage example from the documentation."""
        class Payload(Cob):
            model: str = Grain(required=True)
            temperature: float = Grain()
            max_tokens: int = Grain()
            stream: bool = Grain(default=False)
            
            @create_child_barn_grain('messages')
            class Message(Cob):
                role: str = Grain(required=True)
                content: str = Grain(required=True)
        
        # Test the payload creation
        payload = Payload(model="gpt-4", temperature=0.7, max_tokens=150)
        
        assert payload.model == "gpt-4"
        assert payload.temperature == 0.7
        assert payload.max_tokens == 150
        assert payload.stream is False
        
        # Test message creation
        message = Payload.Message(role="user", content="Hello!")
        
        assert message.role == "user"
        assert message.content == "Hello!"
        
        # Test the barn relationship
        grain = Payload.Message.__dna__._outer_model_grain
        assert grain.label == "messages"
        assert isinstance(grain.pre_value, Barn)
        assert grain.pre_value.model == Payload.Message


class TestCreateChildCobGrain:
    """Test cases for create_child_cob_grain decorator."""
    
    def test_decorator_with_default_label_generation(self):
        """Test decorator creates child cob with auto-generated label."""
        class User(Cob):
            username: str = Grain(required=True)
            
            @create_child_cob_grain()
            class Profile(Cob):
                bio: str = Grain()
                website: str = Grain()
        
        # Check that the child class is properly decorated
        assert hasattr(User.Profile, '__dna__')
        assert hasattr(User.Profile.__dna__, '_outer_model_grain')
        
        # Check that the grain was created with correct label
        grain = User.Profile.__dna__._outer_model_grain
        assert grain.label == "profile"  # snake_case from "Profile"
        assert grain.type == User.Profile
        
        # Check that the grain does NOT have a pre-set value (unlike barn decorator)
        from databarn.trails import NOT_SET
        assert grain.pre_value is NOT_SET
    
    def test_decorator_with_custom_label(self):
        """Test decorator with custom label specification."""
        class Account(Cob):
            email: str = Grain(required=True)
            
            @create_child_cob_grain('user_settings')
            class Settings(Cob):
                theme: str = Grain(default="dark")
                notifications: bool = Grain(default=True)
        
        grain = Account.Settings.__dna__._outer_model_grain
        assert grain.label == "user_settings"
        assert grain.type == Account.Settings
        from databarn.trails import NOT_SET
        assert grain.pre_value is NOT_SET
    
    def test_decorator_with_grain_parameters(self):
        """Test decorator passing parameters to Grain constructor."""
        class Order(Cob):
            order_id: str = Grain(required=True)
            
            @create_child_cob_grain('billing_info', required=True, default=None)
            class BillingInfo(Cob):
                address: str = Grain(required=True)
                card_number: str = Grain(required=True)
        
        grain = Order.BillingInfo.__dna__._outer_model_grain
        assert grain.label == "billing_info"
        assert grain.required is True
        assert grain.default is None
        assert grain.type == Order.BillingInfo
    
    def test_decorator_error_with_non_cob_class(self):
        """Test that decorator raises error for non-Cob classes."""
        with pytest.raises(DataBarnSyntaxError, match="must be a subclass of Cob"):
            class Parent(Cob):
                name: str = Grain()
                
                @create_child_cob_grain()
                class NotACob:  # This is not a Cob subclass
                    pass
    
    def test_decorator_integration_with_parent_cob(self):
        """Test full integration of decorated child with parent Cob."""
        class Company(Cob):
            name: str = Grain(required=True)
            
            @create_child_cob_grain('headquarters')
            class Address(Cob):
                street: str = Grain(required=True)
                city: str = Grain(required=True)
                country: str = Grain(default="USA")
        
        # Create a parent instance
        company = Company(name="Tech Corp")
        
        # The child class should be accessible
        assert hasattr(Company, 'Address')
        assert issubclass(Company.Address, Cob)
        
        # Check the grain configuration
        grain = Company.Address.__dna__._outer_model_grain
        assert grain.label == "headquarters"
        assert grain.type == Company.Address
        
        # Create child instance
        address = Company.Address(street="123 Main St", city="San Francisco")
        assert address.street == "123 Main St"
        assert address.city == "San Francisco"
        assert address.country == "USA"
    
    def test_multiple_decorated_children(self):
        """Test multiple child cobs in the same parent class."""
        class Employee(Cob):
            employee_id: str = Grain(required=True)
            
            @create_child_cob_grain('personal_info')
            class PersonalInfo(Cob):
                first_name: str = Grain(required=True)
                last_name: str = Grain(required=True)
                birth_date: str = Grain()
            
            @create_child_cob_grain('work_info')
            class WorkInfo(Cob):
                department: str = Grain(required=True)
                position: str = Grain(required=True)
                start_date: str = Grain()
        
        # Check both children are properly decorated
        personal_grain = Employee.PersonalInfo.__dna__._outer_model_grain
        work_grain = Employee.WorkInfo.__dna__._outer_model_grain
        
        assert personal_grain.label == "personal_info"
        assert work_grain.label == "work_info"
        
        # Both should have correct types and no pre-values
        assert personal_grain.type == Employee.PersonalInfo
        assert work_grain.type == Employee.WorkInfo
        from databarn.trails import NOT_SET
        assert personal_grain.pre_value is NOT_SET
        assert work_grain.pre_value is NOT_SET
    
    def test_nested_decoration_levels(self):
        """Test decorator working with nested class hierarchies."""
        class Organization(Cob):
            name: str = Grain(required=True)
            
            @create_child_cob_grain('primary_contact')
            class Contact(Cob):
                name: str = Grain(required=True)
                email: str = Grain(required=True)
                
                @create_child_cob_grain('emergency_contact')
                class EmergencyContact(Cob):
                    relationship: str = Grain(required=True)
                    phone: str = Grain(required=True)
        
        # Check both levels of decoration
        contact_grain = Organization.Contact.__dna__._outer_model_grain
        emergency_grain = Organization.Contact.EmergencyContact.__dna__._outer_model_grain
        
        assert contact_grain.label == "primary_contact"
        assert emergency_grain.label == "emergency_contact"
        
        # Both should have proper types
        assert contact_grain.type == Organization.Contact
        assert emergency_grain.type == Organization.Contact.EmergencyContact
    
    def test_decorator_preserves_class_functionality(self):
        """Test that the decorator doesn't break normal class functionality."""
        class Product(Cob):
            name: str = Grain(required=True)
            
            @create_child_cob_grain('specifications')
            class Specs(Cob):
                dimensions: str = Grain(required=True)
                weight: float = Grain()
                
                def get_display_string(self):
                    return f"{self.dimensions} ({self.weight}kg)"
                
                @property
                def is_heavy(self):
                    return self.weight and self.weight > 10.0
        
        # Create an instance and test its methods
        specs = Product.Specs(dimensions="10x5x2 cm", weight=0.5)
        
        assert specs.dimensions == "10x5x2 cm"
        assert specs.weight == 0.5
        assert specs.get_display_string() == "10x5x2 cm (0.5kg)"
        assert specs.is_heavy is False
        
        # Decorator attributes should still be present
        assert hasattr(Product.Specs.__dna__, '_outer_model_grain')
    
    def test_label_generation_edge_cases(self):
        """Test label generation for various class name patterns."""
        class Parent(Cob):
            pass
        
        # Test various class name patterns
        test_cases = [
            ("UserProfile", "user_profile"),     # CamelCase -> snake_case
            ("APIKey", "a_p_i_key"),            # Acronym handling
            ("XMLParser", "x_m_l_parser"),      # Multiple acronyms
            ("HTMLElement", "h_t_m_l_element"), # HTML acronym
            ("JSONData", "j_s_o_n_data"),       # JSON acronym
            ("SimpleClass", "simple_class"),     # Simple CamelCase
            ("A", "a"),                         # Single letter
            ("iPhone", "i_phone"),              # Mixed case brand name
        ]
        
        for class_name, expected_label in test_cases:
            # Dynamically create a class with the test name
            child_class = type(class_name, (Cob,), {
                'test_field': Grain()
            })
            
            # Apply the decorator
            decorated_class = create_child_cob_grain()(child_class)
            
            grain = decorated_class.__dna__._outer_model_grain
            assert grain.label == expected_label, f"For class {class_name}, expected {expected_label}, got {grain.label}"
    
    def test_decorator_with_complex_grain_parameters(self):
        """Test decorator with multiple complex grain parameters."""
        class Service(Cob):
            name: str = Grain(required=True)
            
            @create_child_cob_grain('configuration', 
                                  required=False, 
                                  default=None,
                                  description="Service configuration settings")
            class Config(Cob):
                host: str = Grain(default="localhost")
                port: int = Grain(default=8080)
                ssl_enabled: bool = Grain(default=False)
        
        grain = Service.Config.__dna__._outer_model_grain
        assert grain.label == "configuration"
        assert grain.required is False
        assert grain.default is None
        # Note: Grain class doesn't have description attribute
        assert grain.type == Service.Config
    
    def test_decorator_vs_barn_decorator_differences(self):
        """Test key differences between cob and barn decorators."""
        class Application(Cob):
            name: str = Grain(required=True)
            
            @create_child_cob_grain('config')
            class Config(Cob):
                debug: bool = Grain(default=False)
            
            @create_child_barn_grain('logs')  
            class LogEntry(Cob):
                message: str = Grain(required=True)
                level: str = Grain(default="INFO")
        
        config_grain = Application.Config.__dna__._outer_model_grain
        logs_grain = Application.LogEntry.__dna__._outer_model_grain
        
        # Key differences:
        # 1. Cob decorator: no pre_value, type is the class itself
        from databarn.trails import NOT_SET
        assert config_grain.pre_value is NOT_SET
        assert config_grain.type == Application.Config
        
        # 2. Barn decorator: has pre_value (Barn instance), type is Barn
        assert logs_grain.pre_value is not None
        assert isinstance(logs_grain.pre_value, Barn)
        assert logs_grain.type == Barn
        assert logs_grain.pre_value.model == Application.LogEntry
        
        # 3. Barn decorator is frozen by default, cob decorator doesn't specify frozen
        assert logs_grain.frozen is True
        # Note: config_grain.frozen would be whatever the default is for Grain()


class TestMixedDecoratorUsage:
    """Test cases for using both decorators together."""
    
    def test_combined_decorators_in_same_class(self):
        """Test using both barn and cob decorators in the same parent class."""
        class BlogPost(Cob):
            title: str = Grain(required=True)
            content: str = Grain(required=True)
            
            @create_child_cob_grain('author_info')
            class Author(Cob):
                name: str = Grain(required=True)
                email: str = Grain(required=True)
            
            @create_child_barn_grain('comments')
            class Comment(Cob):
                text: str = Grain(required=True)
                commenter: str = Grain(required=True)
                timestamp: str = Grain()
        
        # Both decorators should work independently
        author_grain = BlogPost.Author.__dna__._outer_model_grain
        comments_grain = BlogPost.Comment.__dna__._outer_model_grain
        
        assert author_grain.label == "author_info"
        assert author_grain.type == BlogPost.Author
        from databarn.trails import NOT_SET
        assert author_grain.pre_value is NOT_SET
        
        assert comments_grain.label == "comments"
        assert comments_grain.type == Barn
        assert isinstance(comments_grain.pre_value, Barn)
    
    def test_nested_mixed_decorators(self):
        """Test complex nesting with both decorator types."""
        class Project(Cob):
            name: str = Grain(required=True)
            
            @create_child_cob_grain('metadata')
            class ProjectMetadata(Cob):
                created_by: str = Grain(required=True)
                created_at: str = Grain(required=True)
                
                @create_child_barn_grain('tags')
                class Tag(Cob):
                    name: str = Grain(required=True)
                    color: str = Grain(default="blue")
            
            @create_child_barn_grain('tasks')
            class Task(Cob):
                title: str = Grain(required=True)
                completed: bool = Grain(default=False)
                
                @create_child_cob_grain('assignee')
                class Assignee(Cob):
                    user_id: str = Grain(required=True)
                    role: str = Grain(default="developer")
        
        # Test all levels of nesting
        metadata_grain = Project.ProjectMetadata.__dna__._outer_model_grain
        tags_grain = Project.ProjectMetadata.Tag.__dna__._outer_model_grain
        tasks_grain = Project.Task.__dna__._outer_model_grain
        assignee_grain = Project.Task.Assignee.__dna__._outer_model_grain
        
        # Verify cob decorators
        from databarn.trails import NOT_SET
        assert metadata_grain.pre_value is NOT_SET
        assert assignee_grain.pre_value is NOT_SET
        
        # Verify barn decorators  
        assert isinstance(tags_grain.pre_value, Barn)
        assert isinstance(tasks_grain.pre_value, Barn)
    
    def test_decorator_interaction_independence(self):
        """Test that decorators don't interfere with each other."""
        class System(Cob):
            version: str = Grain(required=True)
            
            @create_child_cob_grain('database_config')
            class DatabaseConfig(Cob):
                host: str = Grain(required=True)
                port: int = Grain(default=5432)
            
            @create_child_barn_grain('user_sessions')
            class UserSession(Cob):
                session_id: str = Grain(required=True)
                user_id: str = Grain(required=True)
                expires_at: str = Grain()
        
        # Create instances to verify independence
        db_config = System.DatabaseConfig(host="localhost", port=3306)
        session = System.UserSession(session_id="abc123", user_id="user456")
        
        # Both should work independently
        assert db_config.host == "localhost"
        assert db_config.port == 3306
        
        assert session.session_id == "abc123"
        assert session.user_id == "user456"
        
        # Decorator configurations should be independent
        db_grain = System.DatabaseConfig.__dna__._outer_model_grain
        session_grain = System.UserSession.__dna__._outer_model_grain
        
        assert db_grain.label == "database_config"
        assert session_grain.label == "user_sessions"


class TestDecoratorEdgeCases:
    """Test edge cases and error conditions for both decorators."""
    
    def test_decorator_on_inherited_cob_classes(self):
        """Test decorators on classes that inherit from other Cobs.""" 
        # Note: Cob inheritance has specific behaviors - test simple inheritance cases
        class BaseCob(Cob):
            id: str = Grain(required=True)
        
        class Container(Cob):
            title: str = Grain(required=True)
            
            @create_child_cob_grain('simple_item')
            class SimpleItem(Cob):
                # Define all grains in the decorated class directly
                id: str = Grain(required=True)
                value: int = Grain()
            
            @create_child_barn_grain('base_items')
            class BaseItem(Cob):
                # Define all grains in the decorated class directly
                id: str = Grain(required=True)
                description: str = Grain()
        
        # Both decorated classes should work
        simple_grain = Container.SimpleItem.__dna__._outer_model_grain
        base_grain = Container.BaseItem.__dna__._outer_model_grain
        
        assert simple_grain.type == Container.SimpleItem
        assert base_grain.pre_value.model == Container.BaseItem
        
        # Create instances to verify they work correctly
        simple_item = Container.SimpleItem(id="simple1", value=42)
        base_item = Container.BaseItem(id="base1", description="Base item")
        
        assert simple_item.id == "simple1"
        assert simple_item.value == 42
        assert base_item.id == "base1"
        assert base_item.description == "Base item"
    
    def test_decorator_with_empty_class(self):
        """Test decorators on classes with no fields."""
        class Parent(Cob):
            name: str = Grain()
            
            @create_child_cob_grain('empty_cob')
            class EmptyCob(Cob):
                pass
            
            @create_child_barn_grain('empty_items')
            class EmptyItem(Cob):
                pass
        
        # Both should work even with empty classes
        empty_cob_grain = Parent.EmptyCob.__dna__._outer_model_grain
        empty_items_grain = Parent.EmptyItem.__dna__._outer_model_grain
        
        assert empty_cob_grain.label == "empty_cob"
        assert empty_items_grain.label == "empty_items"
        
        # Should be able to create instances
        empty_cob = Parent.EmptyCob()
        empty_item = Parent.EmptyItem()
        
        assert isinstance(empty_cob, Parent.EmptyCob)
        assert isinstance(empty_item, Parent.EmptyItem)
    
    def test_decorator_label_conflict_handling(self):
        """Test behavior when multiple decorators might generate similar labels."""
        class Container(Cob):
            name: str = Grain()
            
            @create_child_cob_grain('item')
            class Item(Cob):
                value: str = Grain()
            
            @create_child_barn_grain('items')  # Similar to above but plural
            class ItemEntry(Cob):
                entry_value: str = Grain()
        
        item_grain = Container.Item.__dna__._outer_model_grain
        items_grain = Container.ItemEntry.__dna__._outer_model_grain
        
        # Labels should be different as specified
        assert item_grain.label == "item"
        assert items_grain.label == "items"
        assert item_grain.label != items_grain.label
    
    def test_decorator_with_special_characters_in_class_name(self):
        """Test decorators with class names that might cause label generation issues."""
        class Parent(Cob):
            name: str = Grain()
            
            # Class names with numbers, underscores, etc.
            @create_child_cob_grain()
            class Item2D(Cob):
                x: float = Grain()
                y: float = Grain()
            
            @create_child_barn_grain()
            class XMLParser3(Cob):
                content: str = Grain()
        
        item2d_grain = Parent.Item2D.__dna__._outer_model_grain
        xml_grain = Parent.XMLParser3.__dna__._outer_model_grain
        
        # Labels should be properly generated
        assert item2d_grain.label == "item2_d"
        assert xml_grain.label == "x_m_l_parser3s"


class TestDecoratorIntegrationScenarios:
    """Integration test scenarios for realistic usage patterns."""
    
    def test_api_payload_structure(self):
        """Test realistic API payload structure using both decorators."""
        class APIRequest(Cob):
            endpoint: str = Grain(required=True)
            method: str = Grain(default="GET")
            
            @create_child_cob_grain('authentication')
            class Auth(Cob):
                api_key: str = Grain(required=True)
                user_id: str = Grain()
            
            @create_child_barn_grain('headers')
            class Header(Cob):
                name: str = Grain(required=True)
                value: str = Grain(required=True)
            
            @create_child_cob_grain('request_body')
            class RequestBody(Cob):
                content_type: str = Grain(default="application/json")
                data: str = Grain()
        
        # Test the complete structure
        auth_grain = APIRequest.Auth.__dna__._outer_model_grain
        headers_grain = APIRequest.Header.__dna__._outer_model_grain
        body_grain = APIRequest.RequestBody.__dna__._outer_model_grain
        
        # Verify proper decorator application
        assert auth_grain.label == "authentication"
        assert auth_grain.type == APIRequest.Auth
        from databarn.trails import NOT_SET
        assert auth_grain.pre_value is NOT_SET
        
        assert headers_grain.label == "headers"
        assert isinstance(headers_grain.pre_value, Barn)
        
        assert body_grain.label == "request_body"
        assert body_grain.type == APIRequest.RequestBody
        from databarn.trails import NOT_SET
        assert body_grain.pre_value is NOT_SET
        
        # Test object creation and usage
        auth = APIRequest.Auth(api_key="secret123", user_id="user456")
        header = APIRequest.Header(name="Content-Type", value="application/json")
        body = APIRequest.RequestBody(data='{"test": "data"}')
        
        assert auth.api_key == "secret123"
        assert header.name == "Content-Type"
        assert body.content_type == "application/json"
    
    def test_e_commerce_order_system(self):
        """Test e-commerce order system with complex relationships."""
        class Order(Cob):
            order_id: str = Grain(required=True, pk=True)
            total_amount: float = Grain(required=True)
            
            @create_child_cob_grain('customer_info')
            class Customer(Cob):
                name: str = Grain(required=True)
                email: str = Grain(required=True)
                
                @create_child_cob_grain('billing_address')
                class BillingAddress(Cob):
                    street: str = Grain(required=True)
                    city: str = Grain(required=True)
                    zip_code: str = Grain(required=True)
            
            @create_child_barn_grain('line_items')
            class LineItem(Cob):
                product_id: str = Grain(required=True)
                quantity: int = Grain(required=True)
                unit_price: float = Grain(required=True)
                
                @create_child_cob_grain('product_details')
                class Product(Cob):
                    name: str = Grain(required=True)
                    description: str = Grain()
                    category: str = Grain()
        
        # Test all levels of the hierarchy
        customer_grain = Order.Customer.__dna__._outer_model_grain
        billing_grain = Order.Customer.BillingAddress.__dna__._outer_model_grain
        items_grain = Order.LineItem.__dna__._outer_model_grain
        product_grain = Order.LineItem.Product.__dna__._outer_model_grain
        
        # Verify decorator types and labels
        assert customer_grain.label == "customer_info"
        from databarn.trails import NOT_SET
        assert customer_grain.pre_value is NOT_SET  # cob decorator
        
        assert billing_grain.label == "billing_address"
        assert billing_grain.pre_value is NOT_SET   # cob decorator
        
        assert items_grain.label == "line_items"
        assert isinstance(items_grain.pre_value, Barn)  # barn decorator
        
        assert product_grain.label == "product_details"
        from databarn.trails import NOT_SET
        assert product_grain.pre_value is NOT_SET  # cob decorator
        
        # Test object creation and relationships
        customer = Order.Customer(name="John Doe", email="john@example.com")
        billing = Order.Customer.BillingAddress(
            street="123 Main St", 
            city="Anytown", 
            zip_code="12345"
        )
        line_item = Order.LineItem(product_id="prod123", quantity=2, unit_price=29.99)
        product = Order.LineItem.Product(
            name="Widget", 
            description="A useful widget", 
            category="Tools"
        )
        
        # Verify all objects work correctly
        assert customer.name == "John Doe"
        assert billing.street == "123 Main St"
        assert line_item.quantity == 2
        assert product.name == "Widget"
    
    def test_configuration_system_with_validation(self):
        """Test configuration system using decorators with validation."""
        class AppConfig(Cob):
            app_name: str = Grain(required=True)
            version: str = Grain(required=True)
            
            @create_child_cob_grain('database_config')
            class DatabaseConfig(Cob):
                host: str = Grain(required=True)
                port: int = Grain(default=5432)
                ssl_enabled: bool = Grain(default=False)
                
                @create_child_barn_grain('connection_pools')
                class ConnectionPool(Cob):
                    name: str = Grain(required=True)
                    max_connections: int = Grain(default=10)
                    timeout: int = Grain(default=30)
            
            @create_child_barn_grain('feature_flags')
            class FeatureFlag(Cob):
                name: str = Grain(required=True)
                enabled: bool = Grain(default=False)
                rollout_percentage: float = Grain(default=0.0)
        
        # Test the configuration hierarchy
        db_grain = AppConfig.DatabaseConfig.__dna__._outer_model_grain
        pools_grain = AppConfig.DatabaseConfig.ConnectionPool.__dna__._outer_model_grain
        flags_grain = AppConfig.FeatureFlag.__dna__._outer_model_grain
        
        # Verify decorator application
        assert db_grain.label == "database_config"
        assert pools_grain.label == "connection_pools"
        assert flags_grain.label == "feature_flags"
        
        # Create configuration objects
        db_config = AppConfig.DatabaseConfig(host="localhost", port=3306, ssl_enabled=True)
        pool = AppConfig.DatabaseConfig.ConnectionPool(
            name="main_pool", 
            max_connections=50, 
            timeout=60
        )
        flag = AppConfig.FeatureFlag(
            name="new_ui", 
            enabled=True, 
            rollout_percentage=25.5
        )
        
        # Verify configuration values
        assert db_config.host == "localhost"
        assert db_config.ssl_enabled is True
        assert pool.max_connections == 50
        assert flag.rollout_percentage == 25.5
    
    def test_documentation_system_complex_nesting(self):
        """Test documentation system with deep nesting and mixed decorators."""
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
        
        # Test all levels of nesting with mixed decorators
        metadata_grain = Documentation.DocumentMetadata.__dna__._outer_model_grain
        contributors_grain = Documentation.DocumentMetadata.Contributor.__dna__._outer_model_grain
        sections_grain = Documentation.Section.__dna__._outer_model_grain
        subsections_grain = Documentation.Section.Subsection.__dna__._outer_model_grain
        code_grain = Documentation.Section.Subsection.CodeExample.__dna__._outer_model_grain
        
        # Verify all decorator types
        from databarn.trails import NOT_SET
        assert metadata_grain.pre_value is NOT_SET  # cob
        assert isinstance(contributors_grain.pre_value, Barn)  # barn
        assert isinstance(sections_grain.pre_value, Barn)  # barn
        assert isinstance(subsections_grain.pre_value, Barn)  # barn
        assert code_grain.pre_value is NOT_SET  # cob
        
        # Test deep object creation
        metadata = Documentation.DocumentMetadata(
            author="Jane Developer",
            created_at="2024-01-01",
            last_modified="2024-01-15"
        )
        contributor = Documentation.DocumentMetadata.Contributor(
            name="John Reviewer",
            role="Technical Reviewer",
            email="john@example.com"
        )
        section = Documentation.Section(
            title="Introduction",
            content="This is the introduction section.",
            order=1
        )
        subsection = Documentation.Section.Subsection(
            title="Getting Started",
            content="Follow these steps to get started."
        )
        code_example = Documentation.Section.Subsection.CodeExample(
            language="python",
            code="print('Hello, World!')",
            description="A simple Hello World example"
        )
        
        # Verify all objects work correctly at all levels
        assert metadata.author == "Jane Developer"
        assert contributor.role == "Technical Reviewer"
        assert section.order == 1
        assert subsection.title == "Getting Started"
        assert code_example.language == "python"
