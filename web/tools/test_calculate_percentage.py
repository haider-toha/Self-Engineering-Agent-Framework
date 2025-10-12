import pytest
from calculate_percentage import calculate_percentage

def test_calculate_percentage_normal_case():
    result = calculate_percentage(100, 25)
    assert result == 25.0, "25% of 100 should be 25.0"

def test_calculate_percentage_decimal_case():
    result = calculate_percentage(90.5, 50)
    assert result == 45.25, "50% of 90.5 should be 45.25"

def test_calculate_percentage_zero_case():
    result = calculate_percentage(0, 50)
    assert result == 0, "50% of 0 should be 0"

def test_calculate_percentage_negative_case():
    with pytest.raises(ValueError):
        calculate_percentage(-100, 25)

def test_calculate_percentage_none_case():
    with pytest.raises(TypeError):
        calculate_percentage(None, 25)

def test_calculate_percentage_wrong_type_case():
    with pytest.raises(TypeError):
        calculate_percentage("100", 25)