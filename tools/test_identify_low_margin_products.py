import pytest
import pandas as pd
import numpy as np
from io import StringIO
from identify_low_margin_products import identify_low_margin_products

def test_identify_low_margin_products_with_real_csv_file():
    # Test with actual file that exists in the sandbox
    result = identify_low_margin_products("data/ecommerce_products.csv", 0.35)
    assert result is not None, "Should process existing CSV file"
    assert result['success'] == True, f"Should successfully load file. Error: {result.get('error', 'unknown')}"
    assert isinstance(result['low_margin_products'], pd.DataFrame), "Result should include a DataFrame"

def test_identify_low_margin_products_with_dataframe():
    # Test with a normal DataFrame
    test_data = pd.DataFrame({
        'price': [100, 200, 300],
        'cost': [50, 150, 250]
    })
    result = identify_low_margin_products(test_data, 0.35)
    assert result['success'] == True, f"Should process DataFrame successfully. Error: {result.get('error', 'unknown')}"
    assert isinstance(result['low_margin_products'], pd.DataFrame), "Result should include a DataFrame"

def test_identify_low_margin_products_division_by_zero():
    # Test edge case with zero price
    zero_price_data = pd.DataFrame({'price': [0, 100], 'cost': [10, 50]})
    result = identify_low_margin_products(zero_price_data, 0.35)
    assert result['success'] == True, "Should handle division by zero gracefully"
    assert not result['low_margin_products'].empty, "Should identify low margin products"

def test_identify_low_margin_products_negative_values():
    # Test edge case with negative values
    negative_values_data = pd.DataFrame({'price': [-100, 200], 'cost': [50, -150]})
    result = identify_low_margin_products(negative_values_data, 0.35)
    assert result['success'] == True, "Should handle negative values gracefully"
    assert isinstance(result['low_margin_products'], pd.DataFrame), "Result should include a DataFrame"

def test_identify_low_margin_products_with_nan_and_inf():
    # Test edge case with NaN and infinity
    nan_inf_data = pd.DataFrame({'price': [np.nan, np.inf, 100], 'cost': [50, 50, np.inf]})
    result = identify_low_margin_products(nan_inf_data, 0.35)
    assert result['success'] == True, "Should handle NaN and infinity gracefully"
    assert isinstance(result['low_margin_products'], pd.DataFrame), "Result should include a DataFrame"

def test_identify_low_margin_products_with_empty_dataframe():
    # Test with an empty DataFrame
    empty_data = pd.DataFrame(columns=['price', 'cost'])
    result = identify_low_margin_products(empty_data, 0.35)
    assert result['success'] == True, "Should handle empty DataFrame gracefully"
    assert result['low_margin_products'].empty, "Result should be an empty DataFrame"

def test_identify_low_margin_products_with_none_input():
    # Test with None as input
    result = identify_low_margin_products(None, 0.35)
    assert result['success'] == False, "Should not succeed with None input"
    assert result['error'] is not None, "Should return an error message"

def test_identify_low_margin_products_with_invalid_data_type():
    # Test with invalid data type
    result = identify_low_margin_products(12345, 0.35)
    assert result['success'] == False, "Should not succeed with invalid data type"
    assert result['error'] is not None, "Should return an error message"