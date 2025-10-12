import pytest
from calculate_factorial import calculate_factorial

def test_calculate_factorial_normal_case():
    result = calculate_factorial(5)
    assert result == 120, "Factorial of 5 should be 120"

def test_calculate_factorial_zero_case():
    result = calculate_factorial(0)
    assert result == 1, "Factorial of 0 should be 1"

def test_calculate_factorial_one_case():
    result = calculate_factorial(1)
    assert result == 1, "Factorial of 1 should be 1"

def test_calculate_factorial_negative_number():
    with pytest.raises(ValueError):
        calculate_factorial(-5)

def test_calculate_factorial_non_integer():
    with pytest.raises(TypeError):
        calculate_factorial(5.5)

def test_calculate_factorial_string_input():
    with pytest.raises(TypeError):
        calculate_factorial("5")