from pricing import add_tax


def test_add_tax_includes_rate():
    assert add_tax(100, 0.2) == 120
    assert add_tax(200, 0.5) == 300
