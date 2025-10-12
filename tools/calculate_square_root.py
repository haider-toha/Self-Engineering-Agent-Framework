import math

def calculate_square_root(number: float) -> float:
    """
    Calculates the square root of a given number. This function is useful for determining the square root of any positive real number.
    For example, calculating the square root of 56 would return approximately 7.483. Commonly used in mathematics, physics, engineering, and statistics.
    Handles both whole numbers and decimals. The function will return an error if a negative number is passed as it's not possible to calculate the square root of a negative number in the real number system.
    Examples: calculate_square_root(56) returns 7.483, calculate_square_root(4) returns 2.0.
    """
    if not isinstance(number, (int, float)):
        raise TypeError("Input must be a number")
    if number < 0:
        raise ValueError("Cannot calculate square root of a negative number")
    return math.sqrt(number)