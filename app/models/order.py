from dataclasses import dataclass


@dataclass
class Order:
    id: int
    status: str
