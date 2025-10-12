import pytest
from calculate_percentage import calculate_percentage


def test_calculate_percentage_basic():
    """Test basic percentage calculation"""
    assert calculate_percentage(100, 50) == 50.0
    assert calculate_percentage(200, 25) == 50.0


def test_calculate_percentage_decimal():
    """Test with decimal percentages"""
    assert calculate_percentage(100, 15.5) == 15.5
    

def test_calculate_percentage_zero():
    """Test with zero values"""
    assert calculate_percentage(100, 0) == 0
    assert calculate_percentage(0, 50) == 0


def test_calculate_percentage_large():
    """Test with large numbers"""
    assert calculate_percentage(1000, 150) == 1500