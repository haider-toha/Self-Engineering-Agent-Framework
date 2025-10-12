def calculate_factorial(n: int) -> int:
    """
    Calculates the factorial of a given number.

    Args:
        n (int): The number for which to calculate the factorial.

    Returns:
        int: The factorial of the given number.
    """
    if n is None or not isinstance(n, int):
        raise TypeError("Input must be an integer")
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    if n == 0:
        return 1
    else:
        factorial = 1
        for i in range(1, n + 1):
            factorial *= i
        return factorial