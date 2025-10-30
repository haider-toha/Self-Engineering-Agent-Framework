import pytest
from calculate_percentage import calculate_percentage

def test_calculate_percentage_normal_case():
    result = calculate_percentage(100, 25)
    assert result == 25.0, "Expected 25% of 100 to be 25.0"

def test_calculate_percentage_zero_base():
    result = calculate_percentage(0, 25)
    assert result == 0.0, "Expected any percentage of 0 to be 0.0"

def test_calculate_percentage_zero_percentage():
    result = calculate_percentage(100, 0)
    assert result == 0.0, "Expected 0% of any number to be 0.0"

def test_calculate_percentage_negative_base():
    result = calculate_percentage(-100, 25)
    assert result == -25.0, "Expected 25% of -100 to be -25.0"

def test_calculate_percentage_negative_percentage():
    result = calculate_percentage(100, -25)
    assert result == -25.0, "Expected -25% of 100 to be -25.0"

def test_calculate_percentage_large_numbers():
    result = calculate_percentage(1e6, 50)
    assert result == 500000.0, "Expected 50% of 1,000,000 to be 500,000.0"

def test_calculate_percentage_decimal_values():
    result = calculate_percentage(100.5, 25.5)
    assert result == 25.6275, "Expected 25.5% of 100.5 to be 25.6275"

def test_calculate_percentage_none_base():
    with pytest.raises(TypeError, match="unsupported operand type"):
        calculate_percentage(None, 25)

def test_calculate_percentage_none_percentage():
    with pytest.raises(TypeError, match="unsupported operand type"):
        calculate_percentage(100, None)

def test_calculate_percentage_string_input():
    with pytest.raises(TypeError, match="unsupported operand type"):
        calculate_percentage("100", "25")