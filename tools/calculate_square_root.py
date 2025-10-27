import math

def calculate_square_root(number: float) -> float:
    """
    Calculates the square root of a given number. This function is useful in mathematical computations
    where determining the square root is necessary, such as in geometry, physics, and various engineering fields.
    The function handles positive numbers and returns the principal square root. For example, the square root of 144 is 12.0.
    If the input is a negative number, the function will raise a ValueError as square roots of negative numbers are not
    defined in the set of real numbers. Examples: calculate_square_root(144) returns 12.0, calculate_square_root(9) returns 3.0.
    """
    if not isinstance(number, (int, float)):
        raise TypeError("Input must be a number")
    if number < 0:
        raise ValueError("math domain error")
    return math.sqrt(number)