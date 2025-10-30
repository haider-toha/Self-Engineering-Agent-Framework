import csv
from typing import List, Dict, Union

def calculate_profit_margins(file_path: str) -> List[Dict[str, Union[str, float, None]]]:
    """
    Loads product data from a CSV file and calculates the profit margin for each product.
    The profit margin is calculated using the formula (price - cost) / price.
    This function is useful for analyzing the profitability of products in an inventory.
    It reads the CSV file specified by the file_path parameter, which should contain columns:
    product_name, price, cost, category, units_sold, and rating.
    The function returns a list of dictionaries, each containing the product name and its corresponding profit margin.
    """
    results = []
    
    try:
        with open(file_path, mode='r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                product_name = row['product_name']
                try:
                    price = float(row['price'])
                    cost = float(row['cost'])
                    
                    if price <= 0:
                        profit_margin = None
                    else:
                        profit_margin = (price - cost) / price
                    
                except ValueError:
                    profit_margin = None
                
                results.append({
                    'product_name': product_name,
                    'profit_margin': profit_margin
                })
    
    except FileNotFoundError:
        raise FileNotFoundError(f"The file at {file_path} was not found.")
    
    return results