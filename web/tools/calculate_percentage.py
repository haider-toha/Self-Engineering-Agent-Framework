def calculate_percentage(total: float, percent: float) -> float:
    """
    This function calculates the percentage of a given total number. It is useful in various scenarios where you need to find out what portion a certain percentage represents of a total value. For instance, if you want to calculate what is 25% of 80, you would use this function. It can handle both whole numbers and decimals. The function takes two parameters: the total number and the percentage you want to calculate. It returns the calculated percentage as a float. Example of usage: calculate_percentage(80, 25) would return 20.0.
    """
    if not isinstance(total, (int, float)) or not isinstance(percent, (int, float)):
        raise TypeError("Both total and percent must be numbers")
    if total < 0 or percent < 0:
        raise ValueError("Both total and percent must be non-negative")
    return (total * percent) / 100