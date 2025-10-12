def reverse_string(input_string: str) -> str:
    """
    Reverses the order of characters in a given string.

    Args:
        input_string (str): The string to be reversed.

    Returns:
        str: The reversed string.
    """
    if not isinstance(input_string, str):
        raise TypeError("Input must be a string")
    return input_string[::-1]