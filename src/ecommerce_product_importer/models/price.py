from dataclasses import dataclass


@dataclass
class Price:
    model: str
    color: str
    size: str
    net_price: float
    recommended_price: float
