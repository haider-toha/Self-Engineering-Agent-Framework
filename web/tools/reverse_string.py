def reverse_string(input_string: str) -> str:
    """
    Reverses the given input string. This function takes a string as input and returns a new string
    with the characters in reverse order. It is useful in scenarios where you need to check for
    palindromes, or simply need the reverse order of characters for processing or display purposes.
    The function handles empty strings by returning an empty string and can manage strings with
    special characters and spaces.
    
    Examples:
    reverse_string('hello') returns 'olleh'
    reverse_string('12345') returns '54321'
    reverse_string('A man, a plan, a canal, Panama') returns 'amanaP ,lanac a ,nalp a ,nam A'
    """
    if input_string is None:
        raise TypeError("Input cannot be None")
    return input_string[::-1]