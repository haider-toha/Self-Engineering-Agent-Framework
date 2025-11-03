import pandas as pd
from typing import Union, Dict, Any

def calculate_profit_margins(data_source: Union[str, pd.DataFrame], output_path: str) -> Dict[str, Any]:
    """
    Loads product data from a CSV file or a DataFrame, calculates the profit margin for each product,
    and saves the results to a specified CSV file. The profit margin is calculated using the formula
    (price - cost) / price. The function returns a dictionary indicating success or failure, and any
    error messages if applicable.
    """
    # Input validation
    if data_source is None:
        return {"success": False, "error": "Data source cannot be None", "output_file": None}
    
    if not isinstance(output_path, str) or not output_path:
        return {"success": False, "error": "Invalid output path", "output_file": None}
    
    # Load data
    try:
        if isinstance(data_source, str):
            try:
                df = pd.read_csv(data_source)
            except FileNotFoundError:
                return {"success": False, "error": "File not found", "output_file": None}
            except pd.errors.EmptyDataError:
                return {"success": False, "error": "CSV file is empty", "output_file": None}
            except Exception as e:
                return {"success": False, "error": f"Error reading CSV file: {str(e)}", "output_file": None}
        elif isinstance(data_source, pd.DataFrame):
            df = data_source
        else:
            return {"success": False, "error": "Invalid data source type", "output_file": None}
        
        # Validate required columns
        if 'price' not in df.columns or 'cost' not in df.columns:
            return {"success": False, "error": "Data must contain 'price' and 'cost' columns", "output_file": None}
        
        # Calculate profit margins
        def calculate_margin(row):
            price = row['price']
            cost = row['cost']
            if pd.isna(price) or pd.isna(cost) or price == 0:
                return None
            return (price - cost) / price
        
        df['profit_margin'] = df.apply(calculate_margin, axis=1)
        
        # Save to CSV
        try:
            df.to_csv(output_path, index=False)
        except Exception as e:
            return {"success": False, "error": f"Error saving CSV file: {str(e)}", "output_file": None}
        
        return {"success": True, "error": None, "output_file": output_path}
    
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}", "output_file": None}