from app.models.order import Order
from app.storage import order_store


def get_order(order_id):
    row = order_store.fetch(order_id)
    return Order(id=row["id"], status=row["status"])
