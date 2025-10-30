def calculate_percentage(base: float, percentage: float) -> float:
    """
    Calculates the percentage of a given base number. This function is useful for determining
    what portion a percentage represents of a total value. For example, calculating 25% of 100
    would return 25.0. Commonly used in financial calculations, statistics, and data analysis.
    Handles both whole numbers and decimals. Examples: calculate_percentage(100, 25) returns 25.0,
    calculate_percentage(80, 25) returns 20.0. Edge cases include calculating 0% of any number,
    which will always return 0.0, and calculating any percentage of 0, which will also return 0.0.
    """
    if not isinstance(base, (int, float)) or not isinstance(percentage, (int, float)):
        raise TypeError("unsupported operand type(s) for calculate_percentage")
    
    return (base * percentage) / 100.0