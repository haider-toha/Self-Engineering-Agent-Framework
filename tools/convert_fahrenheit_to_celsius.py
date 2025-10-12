def convert_fahrenheit_to_celsius(fahrenheit: float) -> float:
    """
    Converts a given temperature from degrees Fahrenheit to degrees Celsius. This function is useful for international temperature conversions, as Fahrenheit is primarily used in the United States, while Celsius is used in most other countries. The formula used for conversion is (Fahrenheit - 32) * 5/9. The function handles both whole numbers and decimals. Examples: convert_fahrenheit_to_celsius(100) returns 37.77777777777778, convert_fahrenheit_to_celsius(32) returns 0.0. If a negative Fahrenheit value is provided, the function will return the corresponding negative Celsius value.
    """
    if not isinstance(fahrenheit, (int, float)):
        raise TypeError("Input must be a number")
    return (fahrenheit - 32) * 5/9