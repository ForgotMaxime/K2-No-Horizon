from src.pricing.tax import calculate_total


def checkout(items, tax_rate):
    return calculate_total(items, tax_rate)
