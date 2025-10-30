import pytest
from identify_underperforming_products import identify_underperforming_products

import pandas as pd
import numpy as np
from io import StringIO


def test_identify_underperforming_products_normal_case():
    products = [
        {'name': 'Product A', 'price': 100.0, 'cost': 60.0, 'margin': 0.4},
        {'name': 'Product B', 'price': 150.0, 'cost': 100.0, 'margin': 0.333},
        {'name': 'Product C', 'price': 200.0, 'cost': 150.0, 'margin': 0.25}
    ]
    margin_threshold = 0.35
    result = identify_underperforming_products(products, margin_threshold)
    assert result == [
        {'name': 'Product B', 'price': 150.0, 'cost': 100.0, 'margin': 0.333},
        {'name': 'Product C', 'price': 200.0, 'cost': 150.0, 'margin': 0.25}
    ], "Should identify products with margin below 0.35"

def test_identify_underperforming_products_empty_list():
    products = []
    margin_threshold = 0.35
    result = identify_underperforming_products(products, margin_threshold)
    assert result == [], "Should return empty list for empty input"

def test_identify_underperforming_products_no_underperformers():
    products = [
        {'name': 'Product A', 'price': 100.0, 'cost': 60.0, 'margin': 0.4},
        {'name': 'Product B', 'price': 150.0, 'cost': 100.0, 'margin': 0.5}
    ]
    margin_threshold = 0.35
    result = identify_underperforming_products(products, margin_threshold)
    assert result == [], "Should return empty list when no products are underperforming"

def test_identify_underperforming_products_with_none_values():
    products = [
        {'name': 'Product A', 'price': 100.0, 'cost': 60.0, 'margin': None},
        {'name': 'Product B', 'price': 150.0, 'cost': 100.0, 'margin': 0.333}
    ]
    margin_threshold = 0.35
    result = identify_underperforming_products(products, margin_threshold)
    assert result == [
        {'name': 'Product B', 'price': 150.0, 'cost': 100.0, 'margin': 0.333}
    ], "Should handle None margin gracefully and identify underperformers"

def test_identify_underperforming_products_invalid_data_type():
    products = [
        {'name': 'Product A', 'price': '100.0', 'cost': 60.0, 'margin': 0.4},
        {'name': 'Product B', 'price': 150.0, 'cost': '100.0', 'margin': 0.333}
    ]
    margin_threshold = 0.35
    result = identify_underperforming_products(products, margin_threshold)
    assert result == [
        {'name': 'Product B', 'price': 150.0, 'cost': '100.0', 'margin': 0.333}
    ], "Should handle invalid data types gracefully"

def test_identify_underperforming_products_negative_margin():
    products = [
        {'name': 'Product A', 'price': 100.0, 'cost': 110.0, 'margin': -0.1},
        {'name': 'Product B', 'price': 150.0, 'cost': 100.0, 'margin': 0.333}
    ]
    margin_threshold = 0.35
    result = identify_underperforming_products(products, margin_threshold)
    assert result == [
        {'name': 'Product A', 'price': 100.0, 'cost': 110.0, 'margin': -0.1},
        {'name': 'Product B', 'price': 150.0, 'cost': 100.0, 'margin': 0.333}
    ], "Should identify products with negative margins as underperforming"

def test_identify_underperforming_products_none_margin_threshold():
    products = [
        {'name': 'Product A', 'price': 100.0, 'cost': 60.0, 'margin': 0.4},
        {'name': 'Product B', 'price': 150.0, 'cost': 100.0, 'margin': 0.333}
    ]
    margin_threshold = None
    with pytest.raises(TypeError):
        identify_underperforming_products(products, margin_threshold)

def test_identify_underperforming_products_large_margin_threshold():
    products = [
        {'name': 'Product A', 'price': 100.0, 'cost': 60.0, 'margin': 0.4},
        {'name': 'Product B', 'price': 150.0, 'cost': 100.0, 'margin': 0.333}
    ]
    margin_threshold = 1.0
    result = identify_underperforming_products(products, margin_threshold)
    assert result == products, "Should return all products when threshold is larger than all margins"