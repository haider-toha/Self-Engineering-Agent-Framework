import pytest
import pandas as pd
from calculate_profit_margins import calculate_profit_margins

def test_calculate_profit_margins_normal_case():
    result = calculate_profit_margins('data/ecommerce_products.csv')
    assert isinstance(result, list), "Result should be a list"
    assert len(result) > 0, "Result list should not be empty"
    for item in result:
        assert 'product_name' in item, "Each item should have a 'product_name' key"
        assert 'profit_margin' in item, "Each item should have a 'profit_margin' key"
        assert isinstance(item['profit_margin'], (float, type(None))), "Profit margin should be a float or None"

def test_calculate_profit_margins_zero_price():
    # Assuming 'data/ecommerce_products.csv' has a product with zero price for testing
    result = calculate_profit_margins('data/ecommerce_products.csv')
    for item in result:
        if item['product_name'] == 'Product with Zero Price':  # Replace with actual product name if known
            assert item['profit_margin'] is None, "Profit margin should be None for zero price"

def test_calculate_profit_margins_negative_price():
    # Assuming 'data/ecommerce_products.csv' has a product with negative price for testing
    result = calculate_profit_margins('data/ecommerce_products.csv')
    for item in result:
        if item['product_name'] == 'Product with Negative Price':  # Replace with actual product name if known
            assert item['profit_margin'] is None, "Profit margin should be None for negative price"

def test_calculate_profit_margins_negative_cost():
    # Assuming 'data/ecommerce_products.csv' has a product with negative cost for testing
    result = calculate_profit_margins('data/ecommerce_products.csv')
    for item in result:
        if item['product_name'] == 'Product with Negative Cost':  # Replace with actual product name if known
            assert isinstance(item['profit_margin'], float), "Profit margin should be a float for negative cost"

def test_calculate_profit_margins_invalid_file_path():
    with pytest.raises(FileNotFoundError):
        calculate_profit_margins('data/non_existent_file.csv')