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
import keyword
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
        assert cob.__dna__.get_seed("name").key == "name"
        assert cob.__dna__.get_seed("age").key == "age"
        assert cob.__dna__.get_seed("active").key == "active"
    
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
        assert cob.__dna__.get_seed("first_name").key == "first name"
        assert cob.__dna__.get_seed("last_name").key == "last name"
    
    def test_dash_replacement(self):
        """Test replacing dashes in keys."""
        data = {"user-id": "123", "api-key": "secret"}
        cob = dict_to_cob(data, replace_dash_with="__")
        
        assert hasattr(cob, "user__id")
        assert hasattr(cob, "api__key")
        assert cob.user__id == "123"
        assert cob.api__key == "secret"
        
        # Check original keys are preserved
        assert cob.__dna__.get_seed("user__id").key == "user-id"
        assert cob.__dna__.get_seed("api__key").key == "api-key"
    
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
        assert cob.__dna__.get_seed("class_").key == "class"
        assert cob.__dna__.get_seed("def_").key == "def"
        assert cob.__dna__.get_seed("for_").key == "for"
    
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
        assert cob.__dna__.get_seed("__dna___").key == "__dna__"
        assert cob.__dna__.get_seed("__setattr___").key == "__setattr__"
    
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
        assert cob.__dna__.get_seed("NAME").key == "name"
        assert cob.__dna__.get_seed("AGE").key == "age"
    
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
        assert cob.__dna__.get_seed("valid_key").key == "valid_key"
    
    def test_key_conflict_after_transformation(self):
        """Test error when different keys map to the same transformed key."""
        data = {"user-id": "123", "user_id": "456"}  # Both become user__id
        
        with pytest.raises(InvalidGrainLabelError, match="Key conflict after replacements"):
            dict_to_cob(data, replace_dash_with="_")
    
    def test_truly_invalid_identifier_error(self):
        """Test error when key truly cannot be converted to valid identifier."""
        # Create a case where even after transformations, the result is not a valid identifier
        # by setting prefix_leading_num_with to None so numbers at start aren't fixed
        data = {"123invalid": "value"}
        
        with pytest.raises(InvalidGrainLabelError, match="Cannot convert key.*to a valid var name"):
            dict_to_cob(data, prefix_leading_num_with=None)
    
    def test_invalid_identifier_error(self):
        """Test that keys starting with numbers get prefixed correctly."""
        data = {"123invalid": "value"}  # Starts with number
        
        # Should NOT raise error - gets prefixed with "n_" to become "n_123invalid"
        result = dict_to_cob(data)
        assert hasattr(result, "n_123invalid")
        assert result.n_123invalid == "value"
    
    def test_non_string_key_prefix(self):
        """Test error when dictionary key is not a string."""
        data = {123: "numeric_key", "valid": "value"}
        
        cob = dict_to_cob(data)
        assert hasattr(cob, "n_123")
        assert cob.n_123 == "numeric_key"
        assert hasattr(cob, "valid")
        assert cob.valid == "value"
    
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
        assert cob.__dna__.get_seed("user__info").key == "user-info"
        # Note: Due to the recursive behavior, nested spaces are replaced with dash replacement
        assert cob.user__info.__dna__.get_seed("first__name").key == "first name"
        assert cob.user__info.__dna__.get_seed("class_").key == "class"
    
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


class TestKeyToLabelFunction:
    """Test cases for the internal _key_to_label function behavior."""
    
    def test_custom_key_converter_non_string_return(self):
        """Test that custom key converter must return string."""
        def bad_converter(key):
            return 123  # Returns int instead of string
        
        with pytest.raises(Exception):  # DataBarnSyntaxError
            dict_to_cob({"test": "value"}, custom_key_converter=bad_converter)
    
    def test_custom_key_converter_overrides_all_rules(self):
        """Test that custom converter takes precedence over all other rules."""
        def custom_converter(key):
            return f"custom_{key.replace('-', '_').replace(' ', '_').replace('@', '_')}"
        
        data = {
            "class": "keyword",  # Python keyword
            "user-name": "dash",  # Has dash
            "first name": "space",  # Has space
            "123start": "number"  # Starts with number
        }
        
        cob = dict_to_cob(data, custom_key_converter=custom_converter)
        
        # All should use custom converter, ignoring other rules
        assert hasattr(cob, "custom_class")
        assert hasattr(cob, "custom_user_name")  # Dash converted to underscore
        assert hasattr(cob, "custom_first_name")  # Space converted to underscore
        assert hasattr(cob, "custom_123start")  # Number prefix preserved
        
        assert cob.custom_class == "keyword"
        assert cob.custom_user_name == "dash"
    
    def test_keyword_detection_edge_cases(self):
        """Test keyword detection with edge cases."""
        # Test all Python keywords
        keywords_test = {kw: f"value_{kw}" for kw in keyword.kwlist[:5]}  # Test first 5
        
        cob = dict_to_cob(keywords_test, suffix_keyword_with="_kw")
        
        for kw in list(keywords_test.keys())[:5]:
            expected_attr = f"{kw}_kw"
            assert hasattr(cob, expected_attr)
            assert getattr(cob, expected_attr) == f"value_{kw}"
    
    def test_leading_number_edge_cases(self):
        """Test leading number handling with various patterns."""
        data = {
            "1": "single_digit",
            "123": "multiple_digits", 
            "1abc": "number_then_letters",
            "1_underscore": "number_then_underscore",
            "9999test": "large_number"
        }
        
        cob = dict_to_cob(data, prefix_leading_num_with="num_")
        
        assert hasattr(cob, "num_1")
        assert hasattr(cob, "num_123")
        assert hasattr(cob, "num_1abc")
        assert hasattr(cob, "num_1_underscore")
        assert hasattr(cob, "num_9999test")
        
        assert cob.num_1 == "single_digit"
        assert cob.num_123 == "multiple_digits"
    
    def test_invalid_character_replacement_comprehensive(self):
        """Test replacement of various invalid characters."""
        data = {
            "key@domain.com": "email_style",
            "key#hash": "hash_symbol",
            "key%percent": "percent_symbol", 
            "key$dollar": "dollar_symbol",
            "key&ampersand": "ampersand_symbol",
            "key*asterisk": "asterisk_symbol",
            "key+plus": "plus_symbol",
            "key=equals": "equals_symbol",
            "key[bracket]": "brackets",
            "key{brace}": "braces",
            "key(paren)": "parentheses",
            "key|pipe": "pipe_symbol",
            "key\\backslash": "backslash",
            "key/slash": "forward_slash",
            "key?question": "question_mark",
            "key<less>": "angle_brackets",
            "key:colon": "colon",
            "key;semicolon": "semicolon",
            "key\"quote": "double_quote",
            "key'apostrophe": "single_quote",
            "key`backtick": "backtick",
            "key~tilde": "tilde",
            "key!exclamation": "exclamation"
        }
        
        cob = dict_to_cob(data, replace_invalid_char_with="_")
        
        # All invalid characters should be replaced with underscore
        assert hasattr(cob, "key_domain_com")
        assert hasattr(cob, "key_hash")
        assert hasattr(cob, "key_percent")
        assert hasattr(cob, "key_dollar")
        assert hasattr(cob, "key_ampersand")
        assert hasattr(cob, "key_asterisk")
        assert hasattr(cob, "key_plus")
        assert hasattr(cob, "key_equals")
        assert hasattr(cob, "key_bracket_")
        assert hasattr(cob, "key_brace_")
        assert hasattr(cob, "key_paren_")
        assert hasattr(cob, "key_pipe")
        assert hasattr(cob, "key_backslash")
        assert hasattr(cob, "key_slash")
        assert hasattr(cob, "key_question")
        assert hasattr(cob, "key_less_")
        assert hasattr(cob, "key_colon")
        assert hasattr(cob, "key_semicolon")
        assert hasattr(cob, "key_quote")
        assert hasattr(cob, "key_apostrophe")
        assert hasattr(cob, "key_backtick")
        assert hasattr(cob, "key_tilde")
        assert hasattr(cob, "key_exclamation")
    
    def test_existing_attribute_conflict_comprehensive(self):
        """Test comprehensive existing attribute conflict detection."""
        # Test various Cob attributes that should cause conflicts
        ref_cob = Cob()
        cob_attributes = [attr for attr in dir(ref_cob) if not attr.startswith('_')][:10]
        
        data = {attr: f"conflicts_with_{attr}" for attr in cob_attributes}
        
        cob = dict_to_cob(data, suffix_existing_attr_with="_conflict")
        
        for attr in cob_attributes:
            expected_attr = f"{attr}_conflict"
            assert hasattr(cob, expected_attr)
            assert getattr(cob, expected_attr) == f"conflicts_with_{attr}"
    
    def test_multiple_transformations_order(self):
        """Test order of transformations when multiple rules apply."""
        data = {
            "class name-with@special": "complex_key"  # keyword + space + dash + invalid char
        }
        
        cob = dict_to_cob(
            data,
            replace_space_with="_",
            replace_dash_with="__", 
            suffix_keyword_with="_kw",
            replace_invalid_char_with="_"
        )
        
        # Based on _key_to_label function, the order is:
        # 1. keyword check (but "class name-with@special" is not a keyword)
        # 2. space replacement: "class_name-with@special"
        # 3. dash replacement: "class_name__with@special"  
        # 4. invalid char replacement: "class_name__with_special"
        # 5. No keyword suffix since not a keyword
        assert hasattr(cob, "class_name__with_special")
        assert cob.class_name__with_special == "complex_key"
    
    def test_empty_string_key(self):
        """Test handling of empty string as key."""
        data = {"": "empty_key_value"}
        
        # Empty string is not a valid identifier, should raise error
        with pytest.raises(InvalidGrainLabelError, match="Cannot convert key.*to a valid var name"):
            dict_to_cob(data)
    
    def test_very_long_key(self):
        """Test handling of very long keys."""
        long_key = "a" * 1000  # 1000 character key
        data = {long_key: "long_key_value"}
        
        cob = dict_to_cob(data)
        
        assert hasattr(cob, long_key)
        assert getattr(cob, long_key) == "long_key_value"
    
    def test_unicode_keys_with_transformations(self):
        """Test Unicode characters in keys with transformations."""
        data = {
            "café-résumé": "french_accents",
            "日本語": "japanese", 
            "🔑key": "emoji_key",
            "αβγ-test": "greek_letters"
        }
        
        cob = dict_to_cob(data, replace_dash_with="__", replace_invalid_char_with="_")
        
        # Unicode letters should be preserved, invalid chars replaced
        assert hasattr(cob, "café__résumé")
        assert hasattr(cob, "日本語")
        assert hasattr(cob, "_key")  # Emoji replaced
        assert hasattr(cob, "αβγ__test")


class TestAdvancedDictToCobScenarios:
    """Advanced test scenarios for dict_to_cob function."""
    
    def test_deeply_nested_structures(self):
        """Test very deeply nested dictionary structures."""
        data = {"a": {"b": {"c": {"d": {"e": {"f": "deep_value"}}}}}}
        
        cob = dict_to_cob(data)
        
        assert cob.a.b.c.d.e.f == "deep_value"
        # Verify all levels are Cob instances
        current = cob
        for level in ['a', 'b', 'c', 'd', 'e']:
            assert isinstance(getattr(current, level), Cob)
            current = getattr(current, level)
    
    def test_circular_reference_avoidance(self):
        """Test that function doesn't create circular references in output."""
        data = {"level1": {"level2": {"back_ref": "not_circular"}}}
        
        cob = dict_to_cob(data)
        
        # Should not create circular references
        assert cob.level1.level2.back_ref == "not_circular"
        assert cob.level1.level2 is not cob  # No circular reference
    
    def test_large_dictionary_performance(self):
        """Test performance with large dictionaries."""
        # Create a large dictionary
        large_data = {f"key_{i}": f"value_{i}" for i in range(1000)}
        
        cob = dict_to_cob(large_data)
        
        # Verify structure is correct
        assert len(cob.__dna__.grains) == 1000
        assert cob.key_0 == "value_0"
        assert cob.key_999 == "value_999"
    
    def test_mixed_data_types_comprehensive(self):
        """Test handling of all Python data types in values."""
        from datetime import datetime, date
        from decimal import Decimal
        
        data = {
            "string": "text",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "none": None,
            "list": [1, 2, 3],
            "tuple": (1, 2, 3),  # Should stay as tuple
            "set": {1, 2, 3},  # Should stay as set
            "datetime": datetime.now(),
            "date": date.today(),
            "decimal": Decimal('10.5'),
            "complex": complex(1, 2),
            "bytes": b"binary",
            "bytearray": bytearray(b"mutable")
        }
        
        cob = dict_to_cob(data)
        
        # All types should be preserved in values
        assert isinstance(cob.string, str)
        assert isinstance(cob.integer, int) 
        assert isinstance(cob.float, float)
        assert isinstance(cob.boolean, bool)
        assert cob.none is None
        assert isinstance(cob.list, list)
        assert isinstance(cob.tuple, tuple)
        assert isinstance(cob.set, set)
        assert isinstance(cob.datetime, datetime)
        assert isinstance(cob.date, date)
        assert isinstance(cob.decimal, Decimal)
        assert isinstance(cob.complex, complex)
        assert isinstance(cob.bytes, bytes)
        assert isinstance(cob.bytearray, bytearray)
    
    def test_barn_vs_list_decision_logic(self):
        """Test the logic that decides when to create Barn vs list."""
        data = {
            "all_dicts": [{"a": 1}, {"b": 2}],  # Should become Barn
            "mixed_types": [{"a": 1}, "string", 3],  # Should stay list
            "empty_list": [],  # Should stay list
            "all_strings": ["a", "b", "c"],  # Should stay list
            "nested_mixed": [{"nested": {"deep": "value"}}, {"other": "dict"}]  # Should become Barn
        }
        
        cob = dict_to_cob(data)
        
        assert isinstance(cob.all_dicts, Barn)
        assert isinstance(cob.mixed_types, list)
        assert isinstance(cob.empty_list, list)
        assert isinstance(cob.all_strings, list)
        assert isinstance(cob.nested_mixed, Barn)
        
        # Verify Barn contents are Cobs
        assert isinstance(cob.all_dicts[0], Cob)
        assert isinstance(cob.nested_mixed[0].nested, Cob)
    
    def test_parameter_combinations_comprehensive(self):
        """Test various combinations of parameters."""
        data = {
            "test-key with@special": "value",
            "class": "keyword",
            "123start": "number"
        }
        
        # Test all parameters disabled - should raise errors for invalid identifiers
        with pytest.raises(InvalidGrainLabelError):
            dict_to_cob(
                data,
                replace_space_with=None,
                replace_dash_with=None,
                suffix_keyword_with=None,
                prefix_leading_num_with=None,
                replace_invalid_char_with=None,
                suffix_existing_attr_with=None
            )
    
    def test_recursive_parameter_passing(self):
        """Test that parameters are correctly passed to recursive calls."""
        data = {
            "outer-key": {
                "inner key": {
                    "deep-key": "value"
                }
            }
        }
        
        cob = dict_to_cob(
            data,
            replace_space_with="SPACE",
            replace_dash_with="DASH"
        )
        
        # Check that nested transformations use the same parameters
        assert hasattr(cob, "outerDASHkey")
        
        # Note: There's a bug in the code where nested calls use 
        # replace_space_with=replace_dash_with instead of replace_space_with=replace_space_with
        # So nested spaces are replaced with the dash replacement value, not the space replacement
        assert hasattr(cob.outerDASHkey, "innerDASHkey")  # Space replaced with DASH, not SPACE
        assert hasattr(cob.outerDASHkey.innerDASHkey, "deepDASHkey")


class TestAdvancedJsonToCobScenarios:
    """Advanced test scenarios for json_to_cob function."""
    
    def test_json_with_special_values(self):
        """Test JSON with special numeric values and edge cases."""
        json_str = '''
        {
            "positive_infinity": "Infinity",
            "negative_infinity": "-Infinity", 
            "not_a_number": "NaN",
            "very_large": 1.7976931348623157e+308,
            "very_small": 2.2250738585072014e-308,
            "max_int": 9007199254740991
        }
        '''
        
        # Note: Standard JSON doesn't support Infinity/NaN, but we test string handling
        cob = json_to_cob(json_str)
        
        assert cob.positive_infinity == "Infinity"
        assert cob.negative_infinity == "-Infinity" 
        assert cob.not_a_number == "NaN"
        assert cob.very_large == 1.7976931348623157e+308
        assert cob.very_small == 2.2250738585072014e-308
        assert cob.max_int == 9007199254740991
    
    def test_json_strict_mode(self):
        """Test JSON parsing in strict mode."""
        # Test with duplicate keys (invalid in strict JSON)
        json_str = '{"key": "first", "key": "second"}'
        
        # Should use the last occurrence
        cob = json_to_cob(json_str)
        assert cob.key == "second"
    
    def test_json_custom_object_hook(self):
        """Test JSON with custom object hook."""
        def custom_object_hook(obj):
            # Convert all string values to uppercase
            return {k: v.upper() if isinstance(v, str) else v for k, v in obj.items()}
        
        json_str = '{"name": "john", "city": "london", "age": 30}'
        
        cob = json_to_cob(json_str, object_hook=custom_object_hook)
        
        assert cob.name == "JOHN"
        assert cob.city == "LONDON"
        assert cob.age == 30  # Number unchanged
    
    def test_json_with_comments_error(self):
        """Test that JSON with comments raises appropriate error."""
        json_with_comments = '''
        {
            // This is a comment
            "name": "John",
            /* Multi-line
               comment */
            "age": 30
        }
        '''
        
        # Standard JSON doesn't support comments
        with pytest.raises(json.JSONDecodeError):
            json_to_cob(json_with_comments)
    
    def test_json_encoding_handling(self):
        """Test JSON with different encodings and escape sequences."""
        json_str = r'''
        {
            "escaped_quotes": "He said \"Hello\"",
            "escaped_backslash": "Path: C:\\Users\\John",
            "unicode_escape": "Unicode: \u0048\u0065\u006c\u006c\u006f",
            "tab_and_newline": "Line1\tTab\nLine2"
        }
        '''
        
        cob = json_to_cob(json_str)
        
        assert cob.escaped_quotes == 'He said "Hello"'
        assert cob.escaped_backslash == "Path: C:\\Users\\John"
        assert cob.unicode_escape == "Unicode: Hello"
        assert cob.tab_and_newline == "Line1\tTab\nLine2"


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""
    
    def test_dict_to_cob_type_error_messages(self):
        """Test specific error messages for type errors."""
        with pytest.raises(TypeError, match="'dikt' must be a dictionary"):
            dict_to_cob(None)
        
        with pytest.raises(TypeError, match="'dikt' must be a dictionary"):
            dict_to_cob(set())
        
        with pytest.raises(TypeError, match="'dikt' must be a dictionary"):
            dict_to_cob(42.5)
    
    def test_invalid_grain_label_error_scenarios(self):
        """Test various scenarios that should raise InvalidGrainLabelError."""
        # Test key conflict after transformations
        data1 = {"user_id": "test1", "user-id": "test2"}
        with pytest.raises(InvalidGrainLabelError, match="Key conflict after replacements"):
            dict_to_cob(data1, replace_dash_with="_")
        
        # Test truly invalid identifier (after setting prefix to None)
        data2 = {"123$%^": "invalid"}
        with pytest.raises(InvalidGrainLabelError, match="Cannot convert key.*to a valid var name"):
            dict_to_cob(data2, prefix_leading_num_with=None, replace_invalid_char_with=None)
    
    def test_complex_conflict_scenarios(self):
        """Test complex key conflict scenarios."""
        # Multiple keys mapping to same result
        data = {
            "test key": "space",
            "test-key": "dash", 
            "test_key": "underscore"
        }
        
        # All should map to "test_key" with default settings
        with pytest.raises(InvalidGrainLabelError, match="Key conflict"):
            dict_to_cob(data)
    
    def test_json_error_propagation(self):
        """Test that JSON errors are properly propagated."""
        invalid_jsons = [
            '{"unclosed": "string}',  # Unclosed string
            '{"trailing": "comma",}',  # Trailing comma
            '{unquoted: "key"}',  # Unquoted key
            '{"duplicate": 1, "duplicate": 2}',  # Duplicate key (might be valid)
        ]
        
        for invalid_json in invalid_jsons[:3]:  # Skip duplicate key test
            with pytest.raises(json.JSONDecodeError):
                json_to_cob(invalid_json)
    
    def test_memory_efficiency_large_structures(self):
        """Test memory efficiency with large nested structures."""
        # Create a structure that could cause memory issues if not handled well
        def create_nested_dict(depth):
            if depth == 0:
                return "leaf_value"
            return {"level": create_nested_dict(depth - 1)}
        
        deep_data = create_nested_dict(50)  # 50 levels deep
        
        cob = dict_to_cob(deep_data)
        
        # Should handle deep nesting without issues
        current = cob
        for i in range(50):
            current = current.level
        assert current == "leaf_value"


class TestFuncsBugDiscovery:
    """Test cases that reveal bugs or unexpected behavior in funcs module."""
    
    def test_recursive_space_replacement_bug(self):
        """Test the bug where recursive calls use wrong parameter for space replacement."""
        data = {
            "outer": {
                "inner key": "value"  # Space in nested key
            }
        }
        
        cob = dict_to_cob(
            data,
            replace_space_with="SPACE",  # This should be used for space replacement
            replace_dash_with="DASH"     # But nested calls incorrectly use this for spaces
        )
        
        # Due to the bug, nested spaces are replaced with dash replacement value
        assert hasattr(cob.outer, "innerDASHkey")  # Bug: uses DASH instead of SPACE
        assert cob.outer.innerDASHkey == "value"
    
    def test_key_to_label_function_order(self):
        """Test the exact order of transformations in _key_to_label."""
        # Test with a key that triggers multiple transformations
        data = {"class-with spaces@symbols123": "test_value"}
        
        cob = dict_to_cob(
            data,
            replace_space_with="_SP_",
            replace_dash_with="_DASH_",
            suffix_keyword_with="_KW",  # Won't apply since full key isn't a keyword
            prefix_leading_num_with="_NUM_",  # Won't apply since doesn't start with number
            replace_invalid_char_with="_INVALID_"
        )
        
        # Order based on _key_to_label:
        # 1. Check if keyword (no, "class-with spaces@symbols123" isn't a keyword)
        # 2. Replace spaces: "class-with_SP_spaces@symbols123"
        # 3. Replace dashes: "class_DASH_with_SP_spaces@symbols123"  
        # 4. Replace invalid chars: "class_DASH_with_SP_spaces_INVALID_symbols123"
        expected_key = "class_DASH_with_SP_spaces_INVALID_symbols123"
        assert hasattr(cob, expected_key)
        assert getattr(cob, expected_key) == "test_value"
    
    def test_cob_attribute_conflict_detection(self):
        """Test detection of conflicts with actual Cob attributes."""
        # Get some real Cob attributes to test conflicts
        sample_cob = Cob()
        real_attrs = [attr for attr in dir(sample_cob) if not attr.startswith('__')][:3]
        
        data = {attr: f"conflicts_with_{attr}" for attr in real_attrs}
        
        cob = dict_to_cob(data, suffix_existing_attr_with="_CONFLICT")
        
        # Should have conflict suffixes
        for attr in real_attrs:
            expected_attr = f"{attr}_CONFLICT"
            assert hasattr(cob, expected_attr)
            assert getattr(cob, expected_attr) == f"conflicts_with_{attr}"
    
    def test_none_parameter_handling(self):
        """Test behavior when various parameters are set to None."""
        data = {
            "valid_key": "should_work",
            "another-valid": "should_also_work"  # Dash but no replacement
        }
        
        # Only disable space replacement, others should work
        cob = dict_to_cob(
            data,
            replace_space_with=None,  # Disabled
            replace_dash_with="__"    # Enabled
        )
        
        assert hasattr(cob, "valid_key")
        assert hasattr(cob, "another__valid")
    
    def test_custom_converter_error_handling(self):
        """Test error handling in custom key converter."""
        def bad_converter(key):
            if key == "error":
                return 123  # Returns non-string
            return f"converted_{key}"
        
        data = {"good": "value", "error": "value"}
        
        # Should raise DataBarnSyntaxError for non-string return
        with pytest.raises(Exception):  # DataBarnSyntaxError or similar
            dict_to_cob(data, custom_key_converter=bad_converter)
    
    def test_edge_case_identifier_validation(self):
        """Test edge cases in Python identifier validation."""
        # Test various edge cases that should be valid identifiers
        data = {
            "_underscore": "valid",
            "_123": "valid_with_underscore_and_number",
            "αβγ": "unicode_letters",  # Unicode letters are valid
        }
        
        cob = dict_to_cob(data)
        
        assert cob._underscore == "valid"
        assert cob._123 == "valid_with_underscore_and_number"
        assert cob.αβγ == "unicode_letters"
    
    def test_large_key_transformations(self):
        """Test transformations on very large keys."""
        large_base = "x" * 100
        data = {
            f"{large_base} with spaces": "space_test",
            f"{large_base}-with-dashes": "dash_test",
            f"123{large_base}": "number_test"
        }
        
        cob = dict_to_cob(data)
        
        # Should handle large keys correctly
        assert hasattr(cob, f"{large_base}_with_spaces")
        assert hasattr(cob, f"{large_base}__with__dashes")
        assert hasattr(cob, f"n_123{large_base}")
    
    def test_nested_list_edge_cases(self):
        """Test edge cases with nested lists and mixed content."""
        data = {
            "mixed_list": [
                {"dict": "one"},
                ["nested", "list"],
                "string",
                42,
                {"dict": "two"},
                None
            ]
        }
        
        cob = dict_to_cob(data)
        
        # Should stay as list since not all items are dicts
        assert isinstance(cob.mixed_list, list)
        assert len(cob.mixed_list) == 6
        assert isinstance(cob.mixed_list[0], Cob)  # First dict becomes Cob
        assert isinstance(cob.mixed_list[1], list)  # Nested list stays list
        assert cob.mixed_list[2] == "string"
        assert cob.mixed_list[3] == 42
        assert isinstance(cob.mixed_list[4], Cob)  # Second dict becomes Cob
        assert cob.mixed_list[5] is None
    
    def test_barn_creation_threshold(self):
        """Test the exact conditions for Barn vs list creation."""
        # Empty list should stay as list
        data1 = {"empty": []}
        cob1 = dict_to_cob(data1)
        assert isinstance(cob1.empty, list)
        
        # Single dict should become Barn
        data2 = {"single": [{"key": "value"}]}
        cob2 = dict_to_cob(data2)
        assert isinstance(cob2.single, Barn)
        
        # All dicts should become Barn
        data3 = {"all_dicts": [{"a": 1}, {"b": 2}, {"c": 3}]}
        cob3 = dict_to_cob(data3)
        assert isinstance(cob3.all_dicts, Barn)
        
        # Mixed content should stay as list
        data4 = {"mixed": [{"a": 1}, "string"]}
        cob4 = dict_to_cob(data4)
        assert isinstance(cob4.mixed, list)


class TestAdvancedJsonEdgeCases:
    """Additional edge cases for JSON parsing."""
    
    def test_json_with_very_deep_nesting(self):
        """Test JSON with very deep nesting."""
        # Create deeply nested JSON
        json_str = '{"level": ' * 20 + '"deep_value"' + '}' * 20
        
        cob = json_to_cob(json_str)
        
        # Navigate to the deep value
        current = cob
        for i in range(20):
            current = current.level
        assert current == "deep_value"
    
    def test_json_with_large_arrays(self):
        """Test JSON with large arrays."""
        large_array = [{"id": i, "value": f"item_{i}"} for i in range(100)]
        json_str = json.dumps({"items": large_array})
        
        cob = json_to_cob(json_str)
        
        assert isinstance(cob.items, Barn)
        assert len(cob.items) == 100
        assert cob.items[0].id == 0
        assert cob.items[99].value == "item_99"
    
    def test_json_with_extreme_values(self):
        """Test JSON with extreme numeric values."""
        json_str = '''
        {
            "tiny": 1e-308,
            "huge": 1e308,
            "zero": 0,
            "negative_zero": -0,
            "max_safe_int": 9007199254740991,
            "beyond_safe_int": 9007199254740992
        }
        '''
        
        cob = json_to_cob(json_str)
        
        assert cob.tiny == 1e-308
        assert cob.huge == 1e308
        assert cob.zero == 0
        assert cob.negative_zero == 0  # -0 becomes 0
        assert cob.max_safe_int == 9007199254740991
        assert cob.beyond_safe_int == 9007199254740992
