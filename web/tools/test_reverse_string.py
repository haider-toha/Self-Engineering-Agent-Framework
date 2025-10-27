import pytest
from reverse_string import reverse_string

def test_reverse_string_normal_case():
    result = reverse_string('hello')
    assert result == 'olleh', "Expected 'olleh' but got {}".format(result)

def test_reverse_string_with_numbers():
    result = reverse_string('12345')
    assert result == '54321', "Expected '54321' but got {}".format(result)

def test_reverse_string_with_special_characters():
    result = reverse_string('A man, a plan, a canal, Panama')
    assert result == 'amanaP ,lanac a ,nalp a ,nam A', "Expected 'amanaP ,lanac a ,nalp a ,nam A' but got {}".format(result)

def test_reverse_string_empty_input():
    result = reverse_string('')
    assert result == '', "Expected '' but got {}".format(result)

def test_reverse_string_none_input():
    with pytest.raises(TypeError):
        reverse_string(None)

def test_reverse_string_single_character():
    result = reverse_string('a')
    assert result == 'a', "Expected 'a' but got {}".format(result)

def test_reverse_string_with_spaces():
    result = reverse_string('  ')
    assert result == '  ', "Expected '  ' but got {}".format(result)

def test_reverse_string_with_mixed_case():
    result = reverse_string('AbCdEfG')
    assert result == 'GfEdCbA', "Expected 'GfEdCbA' but got {}".format(result)

def test_reverse_string_with_unicode():
    result = reverse_string('こんにちは')
    assert result == 'はちにんこ', "Expected 'はちにんこ' but got {}".format(result)