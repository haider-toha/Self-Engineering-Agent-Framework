import pandas as pd
import numpy as np
from typing import Union, Dict, Any

def identify_low_margin_products(product_data: Union[str, pd.DataFrame], margin_threshold: float) -> Dict[str, Any]:
    """
    Identifies products with profit margins below a specified threshold from a given dataset.
    The function accepts either a file path to a CSV or a pandas DataFrame.
    It calculates the profit margin for each product using the formula (price - cost) / price.
    Returns a dictionary containing 'low_margin_products' (a DataFrame of products below the threshold),
    'success' (bool), and 'error' (str or None).
    Handles edge cases such as missing or invalid data, zero or negative prices or costs, and non-existent files.
    """
    # Input validation
    if product_data is None:
        return {"success": False, "low_margin_products": None, "error": "product_data cannot be None"}
    
    if not isinstance(margin_threshold, (float, int)):
        return {"success": False, "low_margin_products": None, "error": "margin_threshold must be a float or int"}
    
    if isinstance(product_data, str):
        try:
            df = pd.read_csv(product_data)
        except FileNotFoundError:
            return {"success": False, "low_margin_products": None, "error": "File not found"}
        except pd.errors.EmptyDataError:
            return {"success": False, "low_margin_products": None, "error": "File is empty"}
        except Exception as e:
            return {"success": False, "low_margin_products": None, "error": f"Error reading file: {str(e)}"}
    elif isinstance(product_data, pd.DataFrame):
        df = product_data
    else:
        return {"success": False, "low_margin_products": None, "error": "Invalid product_data type"}

    # Check for required columns
    if not {'price', 'cost'}.issubset(df.columns):
        return {"success": False, "low_margin_products": None, "error": "DataFrame must contain 'price' and 'cost' columns"}

    # Handle empty DataFrame
    if df.empty:
        return {"success": True, "low_margin_products": pd.DataFrame(columns=['price', 'cost']), "error": None}

    # Calculate profit margin safely
    try:
        df['price'] = pd.to_numeric(df['price'], errors='coerce')
        df['cost'] = pd.to_numeric(df['cost'], errors='coerce')
        
        # Avoid division by zero and handle NaN and inf
        df['profit_margin'] = (df['price'] - df['cost']) / df['price']
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.dropna(subset=['profit_margin'])
        
        # Filter products with low margin
        low_margin_products = df[df['profit_margin'] < margin_threshold]
        
        return {"success": True, "low_margin_products": low_margin_products, "error": None}
    except Exception as e:
        return {"success": False, "low_margin_products": None, "error": f"Unexpected error during calculation: {str(e)}"}