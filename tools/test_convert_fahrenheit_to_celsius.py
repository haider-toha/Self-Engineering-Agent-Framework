import pytest
from convert_fahrenheit_to_celsius import convert_fahrenheit_to_celsius

def test_convert_fahrenheit_to_celsius_normal_case():
    result = convert_fahrenheit_to_celsius(100)
    assert result == 37.77777777777778, "100 degrees Fahrenheit should convert to approximately 37.78 degrees Celsius"

def test_convert_fahrenheit_to_celsius_zero():
    result = convert_fahrenheit_to_celsius(32)
    assert result == 0.0, "32 degrees Fahrenheit should convert to 0 degrees Celsius"

def test_convert_fahrenheit_to_celsius_negative():
    result = convert_fahrenheit_to_celsius(-40)
    assert result == -40.0, "-40 degrees Fahrenheit should convert to -40 degrees Celsius"

def test_convert_fahrenheit_to_celsius_none():
    with pytest.raises(TypeError):
        convert_fahrenheit_to_celsius(None)

def test_convert_fahrenheit_to_celsius_string():
    with pytest.raises(TypeError):
        convert_fahrenheit_to_celsius("100")