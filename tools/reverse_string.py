def reverse_string(input_string: str) -> str:
    """
    Reverses the given input string. This function takes a string as input and returns a new string
    with the characters in reverse order. It is useful for situations where you need to manipulate
    or analyze strings in reverse, such as checking for palindromes or simply displaying text backwards.
    """
    if input_string is None:
        raise TypeError("Input cannot be None")
    return input_string[::-1]