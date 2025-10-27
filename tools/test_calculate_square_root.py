import pytest
from calculate_square_root import calculate_square_root

def test_calculate_square_root_normal_case():
    result = calculate_square_root(144)
    assert result == 12.0, "Expected square root of 144 to be 12.0"

def test_calculate_square_root_small_number():
    result = calculate_square_root(9)
    assert result == 3.0, "Expected square root of 9 to be 3.0"

def test_calculate_square_root_zero():
    result = calculate_square_root(0)
    assert result == 0.0, "Expected square root of 0 to be 0.0"

def test_calculate_square_root_negative_number():
    with pytest.raises(ValueError, match="math domain error"):
        calculate_square_root(-4)

def test_calculate_square_root_float_number():
    result = calculate_square_root(2.25)
    assert result == 1.5, "Expected square root of 2.25 to be 1.5"

def test_calculate_square_root_large_number():
    result = calculate_square_root(1000000)
    assert result == 1000.0, "Expected square root of 1000000 to be 1000.0"

def test_calculate_square_root_none_input():
    with pytest.raises(TypeError):
        calculate_square_root(None)

def test_calculate_square_root_string_input():
    with pytest.raises(TypeError):
        calculate_square_root("16")