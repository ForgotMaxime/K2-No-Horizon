from src.discount import apply_discount


def test_apply_discount_removes_pct():
    assert apply_discount(100, 0.2) == 80
    assert apply_discount(200, 0.5) == 100
