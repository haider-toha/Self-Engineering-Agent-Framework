import pytest
from reverse_string import reverse_string

def test_reverse_string_normal_case():
    result = reverse_string("Hello World")
    assert result == "dlroW olleH", "The string should be reversed"

def test_reverse_string_single_character():
    result = reverse_string("a")
    assert result == "a", "Single character string should return the same character"

def test_reverse_string_empty_string():
    result = reverse_string("")
    assert result == "", "Empty string should return an empty string"

def test_reverse_string_none_input():
    with pytest.raises(TypeError, match="Input must be a string"):
        reverse_string(None)

def test_reverse_string_integer_input():
    with pytest.raises(TypeError, match="Input must be a string"):
        reverse_string(123)

def test_reverse_string_special_characters():
    result = reverse_string("!@#$$%^&*()")
    assert result == ")(*&^%$$#@!", "The string with special characters should be reversed"