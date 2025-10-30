import pytest
import pandas as pd
import numpy as np
from io import StringIO
from calculate_profit_margins import calculate_profit_margins

def test_calculate_profit_margins_with_real_csv_file():
    # Test with actual file that exists in the sandbox
    result = calculate_profit_margins("data/ecommerce_products.csv")
    assert isinstance(result, pd.DataFrame), "Should return a DataFrame"
    assert 'profit_margin' in result.columns, "DataFrame should have 'profit_margin' column"

def test_calculate_profit_margins_with_valid_dataframe():
    # Normal use case with valid DataFrame
    test_data = pd.DataFrame({
        'price': [100, 200, 300],
        'cost': [50, 100, 150]
    })
    result = calculate_profit_margins(test_data)
    assert isinstance(result, pd.DataFrame), "Should return a DataFrame"
    assert 'profit_margin' in result.columns, "DataFrame should have 'profit_margin' column"
    assert result['profit_margin'].equals(pd.Series([0.5, 0.5, 0.5])), "Profit margins should be correctly calculated"

def test_calculate_profit_margins_division_by_zero():
    # Edge case: Division by zero
    test_data = pd.DataFrame({
        'price': [0, 100],
        'cost': [50, 50]
    })
    result = calculate_profit_margins(test_data)
    assert isinstance(result, pd.DataFrame), "Should return a DataFrame"
    assert pd.isna(result.loc[0, 'profit_margin']), "Profit margin should be None for zero price"
    assert result.loc[1, 'profit_margin'] == 0.5, "Profit margin should be correctly calculated"

def test_calculate_profit_margins_with_negative_prices():
    # Edge case: Negative prices
    test_data = pd.DataFrame({
        'price': [-100, 200],
        'cost': [50, 100]
    })
    result = calculate_profit_margins(test_data)
    assert isinstance(result, pd.DataFrame), "Should return a DataFrame"
    assert pd.isna(result.loc[0, 'profit_margin']), "Profit margin should be None for negative price"
    assert result.loc[1, 'profit_margin'] == 0.5, "Profit margin should be correctly calculated"

def test_calculate_profit_margins_with_nan_values():
    # Edge case: NaN values
    test_data = pd.DataFrame({
        'price': [np.nan, 200],
        'cost': [50, np.nan]
    })
    result = calculate_profit_margins(test_data)
    assert isinstance(result, pd.DataFrame), "Should return a DataFrame"
    assert pd.isna(result.loc[0, 'profit_margin']), "Profit margin should be None for NaN price"
    assert pd.isna(result.loc[1, 'profit_margin']), "Profit margin should be None for NaN cost"

def test_calculate_profit_margins_with_empty_dataframe():
    # Edge case: Empty DataFrame
    test_data = pd.DataFrame(columns=['price', 'cost'])
    result = calculate_profit_margins(test_data)
    assert isinstance(result, pd.DataFrame), "Should return a DataFrame"
    assert result.empty, "Result should be an empty DataFrame"

def test_calculate_profit_margins_with_invalid_data_type():
    # True error condition: Invalid data type
    with pytest.raises(TypeError):
        calculate_profit_margins(12345)

def test_calculate_profit_margins_with_none_input():
    # True error condition: None input
    with pytest.raises(ValueError):
        calculate_profit_margins(None)