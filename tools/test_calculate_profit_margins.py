import pytest
import pandas as pd
import numpy as np
from io import StringIO
from calculate_profit_margins import calculate_profit_margins

def test_calculate_profit_margins_with_real_csv_file():
    # Test with actual file that exists in the sandbox
    result = calculate_profit_margins("data/ecommerce_products.csv", "data/profit_margins.csv")
    assert result is not None, "Should process existing CSV file"
    if not result.get('success'):
        print(f"Debug - Error: {result.get('error')}")
        print(f"Debug - Full result: {result}")
    assert result['success'] == True, f"Should successfully load file. Error: {result.get('error', 'unknown')}"
    assert result['output_file'] == "data/profit_margins.csv", "Output file path should be correct"

def test_calculate_profit_margins_with_dataframe():
    # Test with DataFrame input
    test_data = pd.DataFrame({
        'price': [100, 200, 300],
        'cost': [50, 100, 150]
    })
    result = calculate_profit_margins(test_data, "data/profit_margins.csv")
    assert result['success'] == True, "Should successfully calculate profit margins"
    assert result['output_file'] == "data/profit_margins.csv", "Output file path should be correct"

def test_calculate_profit_margins_division_by_zero():
    # Test edge case with division by zero
    zero_data = pd.DataFrame({'price': [0, 100], 'cost': [10, 50]})
    result = calculate_profit_margins(zero_data, "data/profit_margins.csv")
    assert result['success'] == True, "Should handle division by zero gracefully"
    # Check that profit margin for division by zero is None
    assert pd.isna(result['output_file']), "Profit margin for zero price should be None"

def test_calculate_profit_margins_missing_columns():
    # Test with missing columns
    missing_column_data = pd.DataFrame({'price': [100, 200]})
    result = calculate_profit_margins(missing_column_data, "data/profit_margins.csv")
    assert result['success'] == False, "Should fail due to missing 'cost' column"
    assert 'error' in result and result['error'] is not None, "Error message should be provided"

def test_calculate_profit_margins_with_nan_values():
    # Test with NaN values in data
    nan_data = pd.DataFrame({'price': [100, np.nan], 'cost': [50, 20]})
    result = calculate_profit_margins(nan_data, "data/profit_margins.csv")
    assert result['success'] == True, "Should handle NaN values gracefully"
    # Check that profit margin for NaN price is None
    assert pd.isna(result['output_file']), "Profit margin for NaN price should be None"

def test_calculate_profit_margins_with_none_data_source():
    # Test with None as data source
    result = calculate_profit_margins(None, "data/profit_margins.csv")
    assert result['success'] == False, "Should fail with None as data source"
    assert 'error' in result and result['error'] is not None, "Error message should be provided"

def test_calculate_profit_margins_invalid_data_type():
    # Test with invalid data type
    result = calculate_profit_margins(12345, "data/profit_margins.csv")
    assert result['success'] == False, "Should fail with invalid data type"
    assert 'error' in result and result['error'] is not None, "Error message should be provided"