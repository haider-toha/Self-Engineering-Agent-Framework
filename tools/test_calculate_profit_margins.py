import pytest
import pandas as pd
from calculate_profit_margins import calculate_profit_margins

def test_calculate_profit_margins_normal_case():
    result = calculate_profit_margins('data/ecommerce_products.csv')
    assert isinstance(result, list), "Should return a list"
    assert all(isinstance(item, dict) for item in result), "Each item should be a dictionary"
    assert all('product_name' in item and 'profit_margin' in item for item in result), "Each dictionary should have 'product_name' and 'profit_margin' keys"

def test_calculate_profit_margins_zero_price():
    # Assuming 'data/ecommerce_products.csv' has a product with price = 0
    result = calculate_profit_margins('data/ecommerce_products.csv')
    for item in result:
        if item['product_name'] == 'Product with Zero Price':  # Replace with actual product name if known
            assert item['profit_margin'] is None, "Profit margin should be None for zero price"

def test_calculate_profit_margins_negative_price_or_cost():
    # Assuming 'data/ecommerce_products.csv' has a product with negative price or cost
    result = calculate_profit_margins('data/ecommerce_products.csv')
    for item in result:
        if item['product_name'] == 'Product with Negative Price or Cost':  # Replace with actual product name if known
            assert item['profit_margin'] is None, "Profit margin should be None for negative price or cost"

def test_calculate_profit_margins_missing_data():
    # Assuming 'data/ecommerce_products.csv' has a product with missing price or cost
    result = calculate_profit_margins('data/ecommerce_products.csv')
    for item in result:
        if item['product_name'] == 'Product with Missing Data':  # Replace with actual product name if known
            assert item['profit_margin'] is None, "Profit margin should be None for missing data"

def test_calculate_profit_margins_malformed_data():
    # Assuming 'data/ecommerce_products.csv' has a product with non-numeric price or cost
    result = calculate_profit_margins('data/ecommerce_products.csv')
    for item in result:
        if item['product_name'] == 'Product with Malformed Data':  # Replace with actual product name if known
            assert item['profit_margin'] is None, "Profit margin should be None for malformed data"