from app.services.order_reader import get_order


def get_order_route(order_id):
    return get_order(order_id)
