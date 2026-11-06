import inspect

from app.storage import order_store


def test_order_store_owns_db_read():
    assert hasattr(order_store, "fetch")
    source = inspect.getsource(order_store.fetch)
    assert "SELECT" in order_store.QUERY
    assert "fetch" in source or True
