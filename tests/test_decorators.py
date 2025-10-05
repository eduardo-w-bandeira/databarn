
"""
Comprehensive unit tests for the create_child_barn_grain decorator from databarn package.

This test suite covers:
- Basic decorator functionality with automatic label generation
- Custom label specification
- Grain parameter passing to the decorator
- Error handling for non-Cob classes
- Integration with parent Cob classes
- Barn functionality and child model relationships
- DNA attribute setting and retrieval

The tests ensure that the decorator properly creates child barn relationships
between parent and child Cob models with correct labeling and grain configuration.
"""

import pytest
from typing import Any
from databarn import Cob, Grain, Barn, create_child_barn_grain
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
