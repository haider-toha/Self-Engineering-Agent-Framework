import pytest
from calculate_percentage import calculate_percentage

def test_calculate_percentage_normal_case():
    result = calculate_percentage(100, 50)
    assert result == 50.0, "50% of 100 should be 50.0"

def test_calculate_percentage_decimal_case():
    result = calculate_percentage(90, 33.33)
    assert pytest.approx(result, 0.01) == 29.997, "33.33% of 90 should be approximately 29.997"

def test_calculate_percentage_zero_percent():
    result = calculate_percentage(100, 0)
    assert result == 0, "0% of any number should be 0"

def test_calculate_percentage_zero_total():
    result = calculate_percentage(0, 50)
    assert result == 0, "Percentage of 0 should always be 0"

def test_calculate_percentage_negative_percent():
    with pytest.raises(ValueError):
        calculate_percentage(100, -10)

def test_calculate_percentage_negative_total():
    with pytest.raises(ValueError):
        calculate_percentage(-100, 10)

def test_calculate_percentage_non_number_total():
    with pytest.raises(TypeError):
        calculate_percentage("100", 50)

def test_calculate_percentage_non_number_percent():
    with pytest.raises(TypeError):
        calculate_percentage(100, "50")