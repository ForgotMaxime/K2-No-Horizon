from src.pricing.tax import calculate_total


def test_calculate_total_single_tax():
    assert calculate_total([10], 0.1) == 11
