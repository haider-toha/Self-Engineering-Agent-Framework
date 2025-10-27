import pytest
from reverse_string import reverse_string

def test_reverse_string_normal_case():
    result = reverse_string('hello world')
    assert result == 'dlrow olleh', "Expected 'dlrow olleh' but got '{}'".format(result)

def test_reverse_string_single_word():
    result = reverse_string('Python')
    assert result == 'nohtyP', "Expected 'nohtyP' but got '{}'".format(result)

def test_reverse_string_empty_string():
    result = reverse_string('')
    assert result == '', "Expected an empty string but got '{}'".format(result)

def test_reverse_string_single_character():
    result = reverse_string('a')
    assert result == 'a', "Expected 'a' but got '{}'".format(result)

def test_reverse_string_palindrome():
    result = reverse_string('madam')
    assert result == 'madam', "Expected 'madam' but got '{}'".format(result)

def test_reverse_string_with_spaces():
    result = reverse_string(' a b c ')
    assert result == ' c b a ', "Expected ' c b a ' but got '{}'".format(result)

def test_reverse_string_special_characters():
    result = reverse_string('!@#$%^&*()')
    assert result == ')(*&^%$#@!', "Expected ')(*&^%$#@!' but got '{}'".format(result)

def test_reverse_string_numbers():
    result = reverse_string('1234567890')
    assert result == '0987654321', "Expected '0987654321' but got '{}'".format(result)

def test_reverse_string_none_input():
    with pytest.raises(TypeError):
        reverse_string(None)