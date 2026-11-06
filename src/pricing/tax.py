def calculate_total(items, tax_rate):
    subtotal = sum(items)
    taxed = subtotal * (1 + tax_rate)
    return taxed * (1 + tax_rate)
