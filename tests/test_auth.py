from src.auth import is_authorized


def _fresh(value):
    return "".join(list(value))


def test_is_authorized_compares_by_value():
    assert is_authorized(_fresh("Admin"), _fresh("Admin")) is True
    assert is_authorized(_fresh("Admin"), _fresh("Root")) is False
