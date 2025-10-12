def reverse_string(input_string: str) -> str:
    """
    Reverses the order of characters in a given string. This function is useful for manipulating text data, such as in data preprocessing, encryption algorithms, or simply for creating a reversed version of a string. It takes a string as an input and returns a new string where the characters are in the opposite order. For example, reverse_string('hello world') would return 'dlrow olleh'. It handles both single and multi-word strings, as well as strings with special characters. Note that the function does not reverse the order of characters within each word, but the order of characters in the entire string. Examples: reverse_string('hello') returns 'olleh', reverse_string('hello world') returns 'dlrow olleh'.
    """
    if not isinstance(input_string, str):
        raise TypeError("Input must be a string")
    return input_string[::-1]