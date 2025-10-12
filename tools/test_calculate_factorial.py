import pytest
from calculate_factorial import calculate_factorial

def test_calculate_factorial_normal_case():
    result = calculate_factorial(5)
    assert result == 120, "Factorial of 5 should be 120"

def test_calculate_factorial_zero_case():
    result = calculate_factorial(0)
    assert result == 1, "Factorial of 0 should be 1"

def test_calculate_factorial_negative_case():
    with pytest.raises(ValueError) as e:
        calculate_factorial(-5)
    assert str(e.value) == "Factorial is not defined for negative numbers", "Should raise ValueError for negative numbers"

def test_calculate_factorial_non_integer_case():
    with pytest.raises(TypeError) as e:
        calculate_factorial(5.5)
    assert str(e.value) == "Input must be an integer", "Should raise TypeError for non-integer inputs"

def test_calculate_factorial_none_case():
    with pytest.raises(TypeError) as e:
        calculate_factorial(None)
    assert str(e.value) == "Input must be an integer", "Should raise TypeError for None input"