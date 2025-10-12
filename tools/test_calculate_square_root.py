import pytest
from calculate_square_root import calculate_square_root

def test_calculate_square_root_normal_case():
    result = calculate_square_root(4)
    assert result == 2.0, "Square root of 4 should be 2.0"

def test_calculate_square_root_decimal_case():
    result = calculate_square_root(2.25)
    assert result == 1.5, "Square root of 2.25 should be 1.5"

def test_calculate_square_root_large_number_case():
    result = calculate_square_root(1000000)
    assert result == 1000.0, "Square root of 1000000 should be 1000.0"

def test_calculate_square_root_zero_case():
    result = calculate_square_root(0)
    assert result == 0.0, "Square root of 0 should be 0.0"

def test_calculate_square_root_negative_number_case():
    with pytest.raises(ValueError):
        calculate_square_root(-4)

def test_calculate_square_root_wrong_type_case():
    with pytest.raises(TypeError):
        calculate_square_root("4")