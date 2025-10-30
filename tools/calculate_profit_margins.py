import csv
from typing import List, Dict, Union

def calculate_profit_margins(file_path: str) -> List[Dict[str, Union[str, None]]]:
    """
    Loads product data from a CSV file and calculates the profit margin for each product.
    The profit margin is calculated using the formula (price - cost) / price.
    This function is useful for analyzing the profitability of products in an e-commerce setting.
    
    Parameters:
    - file_path (str): The path to the CSV file containing columns: product_name, price, cost, category, units_sold, rating.
    
    Returns:
    - list: A list of dictionaries, each containing the product name and its corresponding profit margin.
    """
    results = []
    
    try:
        with open(file_path, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                product_name = row.get('product_name', '')
                try:
                    price = float(row.get('price', ''))
                    cost = float(row.get('cost', ''))
                    
                    if price <= 0 or cost < 0:
                        profit_margin = None
                    else:
                        profit_margin = (price - cost) / price

                except (ValueError, TypeError):
                    profit_margin = None

                results.append({
                    'product_name': product_name,
                    'profit_margin': profit_margin
                })

    except FileNotFoundError:
        raise FileNotFoundError(f"The file at {file_path} was not found.")
    except Exception as e:
        raise Exception(f"An error occurred while processing the file: {e}")

    return results