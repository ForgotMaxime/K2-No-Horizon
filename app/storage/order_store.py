"""Database read layer. Contains the SQL query for orders."""

QUERY = "SELECT id, status FROM orders WHERE id = ?"


def fetch(order_id):
    # In production this executes QUERY; here it returns a stub row.
    return {"id": order_id, "status": "STALE"}
