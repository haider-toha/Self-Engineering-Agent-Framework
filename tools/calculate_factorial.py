def calculate_factorial(n: int) -> int:
    """
    Calculates the factorial of a given number. The factorial of a non-negative integer n is the product of all positive integers less than or equal to n. It is denoted by n!. This function is useful in mathematics, especially in permutations and combinations, as it represents the number of ways an event can occur. For example, the factorial of 5 (denoted as 5!) is 1*2*3*4*5 = 120. The function only accepts non-negative integers. If a negative number is passed, the function will raise a ValueError. Example: calculate_factorial(5) returns 120.
    """
    if not isinstance(n, int):
        raise TypeError("Input must be a non-negative integer")
    if n < 0:
        raise ValueError("Input must be a non-negative integer")
    factorial = 1
    for i in range(1, n + 1):
        factorial *= i
    return factorial