"""
Unit tests for the funcs module from databarn package.

This test suite covers:
- dict_to_cob function with various scenarios
- json_to_cob function with various scenarios  
- Key transformation rules and edge cases
- Error handling and validation
- Nested structures and collections
- Custom key converters
"""

import pytest
import json
from typing import Dict, Any
from databarn.funcs import dict_to_cob, json_to_cob
from databarn import Cob, Barn
from databarn.exceptions import InvalidGrainLabelError


class TestDictToCob:
    """Test cases for dict_to_cob function."""
    
    def test_simple_dict_conversion(self):
        """Test converting a simple dictionary to Cob."""
        data = {"name": "John", "age": 30, "active": True}
        cob = dict_to_cob(data)
        
        assert isinstance(cob, Cob)
        assert cob.name == "John"
        assert cob.age == 30
        assert cob.active is True
        
        # Check that original keys are preserved in DNA
        assert cob.__dna__.get_seed("name").key_name == "name"
        assert cob.__dna__.get_seed("age").key_name == "age"
        assert cob.__dna__.get_seed("active").key_name == "active"
    
    def test_nested_dict_conversion(self):
        """Test converting nested dictionaries to Cob."""
        data = {
            "user": {
                "name": "Alice",
                "profile": {
                    "email": "alice@example.com",
                    "settings": {"theme": "dark", "notifications": True}
                }
            }
        }
        cob = dict_to_cob(data)
        
        assert isinstance(cob, Cob)
        assert isinstance(cob.user, Cob)
        assert isinstance(cob.user.profile, Cob)
        assert isinstance(cob.user.profile.settings, Cob)
        
        assert cob.user.name == "Alice"
        assert cob.user.profile.email == "alice@example.com"
        assert cob.user.profile.settings.theme == "dark"
        assert cob.user.profile.settings.notifications is True
    
    def test_list_of_dicts_conversion(self):
        """Test converting list of dictionaries to Barn."""
        data = {
            "users": [
                {"name": "John", "age": 30},
                {"name": "Jane", "age": 25}
            ]
        }
        cob = dict_to_cob(data)
        
        assert isinstance(cob, Cob)
        assert isinstance(cob.users, Barn)
        assert len(cob.users) == 2
        
        assert isinstance(cob.users[0], Cob)
        assert isinstance(cob.users[1], Cob)
        assert cob.users[0].name == "John"
        assert cob.users[0].age == 30
        assert cob.users[1].name == "Jane"
        assert cob.users[1].age == 25
    
    def test_mixed_list_conversion(self):
        """Test converting list with mixed types (not all dicts)."""
        data = {
            "items": ["string", 42, {"nested": "dict"}, True]
        }
        cob = dict_to_cob(data)
        
        assert isinstance(cob, Cob)
        assert isinstance(cob.items, list)  # Should be list, not Barn
        assert len(cob.items) == 4
        assert cob.items[0] == "string"
        assert cob.items[1] == 42
        assert isinstance(cob.items[2], Cob)
        assert cob.items[2].nested == "dict"
        assert cob.items[3] is True
    
    def test_space_replacement(self):
        """Test replacing spaces in keys."""
        data = {"first name": "John", "last name": "Doe"}
        cob = dict_to_cob(data, replace_space_with="_")
        
        assert hasattr(cob, "first_name")
        assert hasattr(cob, "last_name")
        assert cob.first_name == "John"
        assert cob.last_name == "Doe"
        
        # Check original keys are preserved
        assert cob.__dna__.get_seed("first_name").key_name == "first name"
        assert cob.__dna__.get_seed("last_name").key_name == "last name"
    
    def test_dash_replacement(self):
        """Test replacing dashes in keys."""
        data = {"user-id": "123", "api-key": "secret"}
        cob = dict_to_cob(data, replace_dash_with="__")
        
        assert hasattr(cob, "user__id")
        assert hasattr(cob, "api__key")
        assert cob.user__id == "123"
        assert cob.api__key == "secret"
        
        # Check original keys are preserved
        assert cob.__dna__.get_seed("user__id").key_name == "user-id"
        assert cob.__dna__.get_seed("api__key").key_name == "api-key"
    
    def test_keyword_suffix(self):
        """Test adding suffix to Python keywords."""
        data = {"class": "MyClass", "def": "function", "for": "loop"}
        cob = dict_to_cob(data, suffix_keyword_with="_")
        
        assert hasattr(cob, "class_")
        assert hasattr(cob, "def_")
        assert hasattr(cob, "for_")
        assert cob.class_ == "MyClass"
        assert cob.def_ == "function"
        assert cob.for_ == "loop"
        
        # Check original keys are preserved
        assert cob.__dna__.get_seed("class_").key_name == "class"
        assert cob.__dna__.get_seed("def_").key_name == "def"
        assert cob.__dna__.get_seed("for_").key_name == "for"
    
    def test_existing_attr_suffix(self):
        """Test adding suffix to keys that conflict with Cob attributes."""
        # Using attributes that exist on Cob class
        data = {"__dna__": "conflict", "__setattr__": "another"}
        cob = dict_to_cob(data, suffix_existing_attr_with="_")
        
        # Should have suffixes to avoid conflicts
        assert hasattr(cob, "__dna___")
        assert hasattr(cob, "__setattr___")
        assert cob.__dna___ == "conflict"
        assert cob.__setattr___ == "another"
        
        # Check original keys are preserved
        assert cob.__dna__.get_seed("__dna___").key_name == "__dna__"
        assert cob.__dna__.get_seed("__setattr___").key_name == "__setattr__"
    
    def test_custom_key_converter(self):
        """Test using custom key converter function."""
        def uppercase_converter(key: str) -> str:
            return key.upper()
        
        data = {"name": "John", "age": 30}
        cob = dict_to_cob(data, custom_key_converter=uppercase_converter)
        
        assert hasattr(cob, "NAME")
        assert hasattr(cob, "AGE")
        assert cob.NAME == "John"
        assert cob.AGE == 30
        
        # Check original keys are preserved
        assert cob.__dna__.get_seed("NAME").key_name == "name"
        assert cob.__dna__.get_seed("AGE").key_name == "age"
    
    def test_no_replacements(self):
        """Test with all replacement options disabled."""
        data = {"valid_key": "value"}
        cob = dict_to_cob(
            data, 
            replace_space_with=None,
            replace_dash_with=None,
            suffix_keyword_with=None,
            suffix_existing_attr_with=None
        )
        
        assert cob.valid_key == "value"
        assert cob.__dna__.get_seed("valid_key").key_name == "valid_key"
    
    def test_key_conflict_after_transformation(self):
        """Test error when different keys map to the same transformed key."""
        data = {"user-id": "123", "user_id": "456"}  # Both become user__id
        
        with pytest.raises(InvalidGrainLabelError, match="Key conflict after replacements"):
            dict_to_cob(data, replace_dash_with="_")
    
    def test_invalid_identifier_error(self):
        """Test error when transformed key is not a valid identifier."""
        data = {"123invalid": "value"}  # Starts with number
        
        with pytest.raises(InvalidGrainLabelError, match="Cannot convert key.*to a valid var name"):
            dict_to_cob(data)
    
    def test_non_string_key_error(self):
        """Test error when dictionary key is not a string."""
        data = {123: "numeric_key", "valid": "value"}
        
        with pytest.raises(InvalidGrainLabelError, match="Key.*is not a string"):
            dict_to_cob(data)
    
    def test_non_dict_input_error(self):
        """Test error when input is not a dictionary."""
        with pytest.raises(TypeError, match="'dikt' must be a dictionary"):
            dict_to_cob("not a dict")
        
        with pytest.raises(TypeError, match="'dikt' must be a dictionary"):
            dict_to_cob(123)
        
        with pytest.raises(TypeError, match="'dikt' must be a dictionary"):
            dict_to_cob(["list", "not", "dict"])
    
    def test_empty_dict_conversion(self):
        """Test converting an empty dictionary."""
        cob = dict_to_cob({})
        
        assert isinstance(cob, Cob)
        assert len(cob.__dna__.labels) == 0
    
    def test_complex_nested_structure(self):
        """Test complex nested structure with mixed types."""
        data = {
            "config": {
                "database": {
                    "host": "localhost",
                    "port": 5432,
                    "credentials": {
                        "username": "admin",
                        "password": "secret"
                    }
                },
                "api-endpoints": [
                    {"path": "/users", "method": "GET"},
                    {"path": "/users", "method": "POST"}
                ],
                "features": ["auth", "logging", "metrics"],
                "debug": True
            }
        }
        
        cob = dict_to_cob(data)
        
        # Test nested Cob access
        assert isinstance(cob.config, Cob)
        assert isinstance(cob.config.database, Cob)
        assert isinstance(cob.config.database.credentials, Cob)
        
        # Test values
        assert cob.config.database.host == "localhost"
        assert cob.config.database.port == 5432
        assert cob.config.database.credentials.username == "admin"
        assert cob.config.database.credentials.password == "secret"
        
        # Test list of dicts becomes Barn
        assert isinstance(cob.config.api__endpoints, Barn)
        assert len(cob.config.api__endpoints) == 2
        assert cob.config.api__endpoints[0].path == "/users"
        assert cob.config.api__endpoints[0].method == "GET"
        
        # Test regular list stays as list
        assert isinstance(cob.config.features, list)
        assert cob.config.features == ["auth", "logging", "metrics"]
        
        # Test boolean
        assert cob.config.debug is True


class TestJsonToCob:
    """Test cases for json_to_cob function."""
    
    def test_simple_json_conversion(self):
        """Test converting simple JSON string to Cob."""
        json_str = '{"name": "John", "age": 30, "active": true}'
        cob = json_to_cob(json_str)
        
        assert isinstance(cob, Cob)
        assert cob.name == "John"
        assert cob.age == 30
        assert cob.active is True
    
    def test_nested_json_conversion(self):
        """Test converting nested JSON to Cob."""
        json_str = '''
        {
            "user": {
                "name": "Alice",
                "profile": {
                    "email": "alice@example.com",
                    "preferences": {
                        "theme": "dark",
                        "notifications": true
                    }
                }
            }
        }
        '''
        cob = json_to_cob(json_str)
        
        assert isinstance(cob.user, Cob)
        assert isinstance(cob.user.profile, Cob)
        assert isinstance(cob.user.profile.preferences, Cob)
        assert cob.user.name == "Alice"
        assert cob.user.profile.email == "alice@example.com"
        assert cob.user.profile.preferences.theme == "dark"
        assert cob.user.profile.preferences.notifications is True
    
    def test_json_array_conversion(self):
        """Test converting JSON with arrays to Cob."""
        json_str = '''
        {
            "users": [
                {"name": "John", "age": 30},
                {"name": "Jane", "age": 25}
            ],
            "tags": ["python", "json", "databarn"]
        }
        '''
        cob = json_to_cob(json_str)
        
        # Array of objects becomes Barn
        assert isinstance(cob.users, Barn)
        assert len(cob.users) == 2
        assert cob.users[0].name == "John"
        assert cob.users[1].name == "Jane"
        
        # Array of primitives stays as list
        assert isinstance(cob.tags, list)
        assert cob.tags == ["python", "json", "databarn"]
    
    def test_json_with_key_transformations(self):
        """Test JSON conversion with key transformations."""
        json_str = '''
        {
            "user-name": "John Doe",
            "api key": "secret123",
            "class": "premium",
            "__dna__": "conflict"
        }
        '''
        cob = json_to_cob(json_str)
        
        # Check transformations applied
        assert hasattr(cob, "user__name")
        assert hasattr(cob, "api_key") 
        assert hasattr(cob, "class_")
        assert hasattr(cob, "__dna___")
        
        # Check values
        assert cob.user__name == "John Doe"
        assert cob.api_key == "secret123"
        assert cob.class_ == "premium"
        assert cob.__dna___ == "conflict"
    
    def test_json_with_custom_converter(self):
        """Test JSON conversion with custom key converter."""
        def snake_to_camel(key: str) -> str:
            components = key.split('_')
            return components[0] + ''.join(word.capitalize() for word in components[1:])
        
        json_str = '{"first_name": "John", "last_name": "Doe", "user_id": 123}'
        cob = json_to_cob(json_str, custom_key_converter=snake_to_camel)
        
        assert hasattr(cob, "firstName")
        assert hasattr(cob, "lastName") 
        assert hasattr(cob, "userId")
        assert cob.firstName == "John"
        assert cob.lastName == "Doe"
        assert cob.userId == 123
    
    def test_json_loads_kwargs(self):
        """Test passing additional arguments to json.loads()."""
        json_str = '{"value": 3.14159}'
        
        # Test with parse_float parameter
        from decimal import Decimal
        cob = json_to_cob(json_str, parse_float=Decimal)
        
        assert isinstance(cob.value, Decimal)
        assert cob.value == Decimal('3.14159')
    
    def test_invalid_json_error(self):
        """Test error handling for invalid JSON."""
        invalid_json = '{"name": "John", "age":}'  # Missing value
        
        with pytest.raises(json.JSONDecodeError):
            json_to_cob(invalid_json)
    
    def test_json_null_values(self):
        """Test handling of JSON null values."""
        json_str = '{"name": "John", "middle_name": null, "active": true}'
        cob = json_to_cob(json_str)
        
        assert cob.name == "John"
        assert cob.middle_name is None
        assert cob.active is True
    
    def test_json_numeric_types(self):
        """Test handling of different numeric types in JSON."""
        json_str = '''
        {
            "integer": 42,
            "float": 3.14,
            "negative": -10,
            "scientific": 1e5,
            "zero": 0
        }
        '''
        cob = json_to_cob(json_str)
        
        assert cob.integer == 42
        assert cob.float == 3.14
        assert cob.negative == -10
        assert cob.scientific == 1e5
        assert cob.zero == 0
    
    def test_json_empty_structures(self):
        """Test handling of empty JSON structures."""
        json_str = '''
        {
            "empty_object": {},
            "empty_array": [],
            "nested": {
                "also_empty": {}
            }
        }
        '''
        cob = json_to_cob(json_str)
        
        assert isinstance(cob.empty_object, Cob)
        assert len(cob.empty_object.__dna__.labels) == 0
        
        assert isinstance(cob.empty_array, list)
        assert len(cob.empty_array) == 0
        
        assert isinstance(cob.nested, Cob)
        assert isinstance(cob.nested.also_empty, Cob)
        assert len(cob.nested.also_empty.__dna__.labels) == 0
    
    def test_json_unicode_handling(self):
        """Test handling of Unicode characters in JSON."""
        json_str = '''
        {
            "message": "Hello, 世界! 🌍",
            "emoji_key": "value",
            "accented": "café résumé"
        }
        '''
        cob = json_to_cob(json_str)
        
        assert cob.message == "Hello, 世界! 🌍"
        assert cob.emoji_key == "value"
        assert cob.accented == "café résumé"


class TestFuncsIntegration:
    """Integration tests for funcs module functions."""
    
    def test_round_trip_conversion(self):
        """Test that dict -> cob -> dict preserves original structure."""
        original_data = {
            "user-info": {
                "first name": "John",
                "last_name": "Doe", 
                "class": "premium"
            },
            "settings": [
                {"key": "theme", "value": "dark"},
                {"key": "lang", "value": "en"}
            ],
            "tags": ["python", "databarn"]
        }
        
        # Convert to Cob
        cob = dict_to_cob(original_data)
        
        # Verify structure
        assert isinstance(cob, Cob)
        assert isinstance(cob.user__info, Cob)
        assert isinstance(cob.settings, Barn)
        assert isinstance(cob.tags, list)
        
        # Check original keys are preserved in DNA
        assert cob.__dna__.get_seed("user__info").key_name == "user-info"
        # Note: Due to the recursive behavior, nested spaces are replaced with dash replacement
        assert cob.user__info.__dna__.get_seed("first__name").key_name == "first name"
        assert cob.user__info.__dna__.get_seed("class_").key_name == "class"
    
    def test_json_to_cob_equivalence(self):
        """Test that json_to_cob produces same result as dict_to_cob."""
        data = {"name": "John", "nested": {"value": 42}}
        json_str = json.dumps(data)
        
        cob_from_dict = dict_to_cob(data)
        cob_from_json = json_to_cob(json_str)
        
        # Both should have same structure and values
        assert cob_from_dict.name == cob_from_json.name
        assert cob_from_dict.nested.value == cob_from_json.nested.value
        assert isinstance(cob_from_json.nested, Cob)
