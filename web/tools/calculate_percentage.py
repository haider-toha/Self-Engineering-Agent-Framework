def calculate_percentage(total: float, percentage: float) -> float:
    """
    This function calculates the percentage of a given total number. It is useful in various fields such as finance, 
    statistics, and data analysis where determining the portion of a total that a percentage represents is necessary. 
    The function accepts two parameters: the total number and the percentage to be calculated. It returns the calculated 
    percentage value as a float. For example, to calculate what 25 percent of 80 is, you would call the function as 
    follows: calculate_percentage(80, 25), which would return 20.0. The function handles both whole numbers and decimals.
    """
    if total is None or not isinstance(total, (int, float)):
        raise TypeError("Total must be a number")
    if total < 0:
        raise ValueError("Total cannot be negative")
    if percentage is None or not isinstance(percentage, (int, float)):
        raise TypeError("Percentage must be a number")
    if percentage < 0 or percentage > 100:
        raise ValueError("Percentage must be between 0 and 100")
    
    return (total * percentage) / 100