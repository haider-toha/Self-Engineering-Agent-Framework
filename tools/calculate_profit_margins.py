import pandas as pd
import numpy as np
from typing import Union

def calculate_profit_margins(data_source: Union[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Loads product data from a CSV file or a DataFrame and calculates the profit margin for each product.
    The profit margin is calculated using the formula (price - cost) / price.
    Returns a DataFrame with an additional column 'profit_margin'.
    Handles edge cases such as missing or null values in 'price' or 'cost', division by zero, and invalid data types.
    If 'price' is zero or negative, the profit margin is set to None for that product.
    If the file path is invalid or the CSV is corrupted, raises an appropriate error.
    Example usage: calculate_profit_margins('data/ecommerce_products.csv') or calculate_profit_margins(df) where df is a DataFrame with the required columns.
    """
    # Input validation
    if data_source is None:
        raise ValueError("Input data_source cannot be None")
    
    if isinstance(data_source, str):
        try:
            df = pd.read_csv(data_source)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {data_source}")
        except pd.errors.EmptyDataError:
            raise ValueError(f"File is empty or corrupted: {data_source}")
        except Exception as e:
            raise ValueError(f"An error occurred while reading the file: {str(e)}")
    elif isinstance(data_source, pd.DataFrame):
        df = data_source
    else:
        raise TypeError("data_source must be a string file path or a pandas DataFrame")
    
    # Ensure required columns are present
    if not {'price', 'cost'}.issubset(df.columns):
        raise ValueError("DataFrame must contain 'price' and 'cost' columns")
    
    # Calculate profit margin with edge case handling
    def calculate_margin(row):
        price = row['price']
        cost = row['cost']
        
        if pd.isna(price) or pd.isna(cost):
            return None
        if price <= 0:
            return None
        return (price - cost) / price
    
    df['profit_margin'] = df.apply(calculate_margin, axis=1)
    
    return df