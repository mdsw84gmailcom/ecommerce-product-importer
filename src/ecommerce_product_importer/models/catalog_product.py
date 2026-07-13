from dataclasses import dataclass


@dataclass
class CatalogProduct:
    article_number: str
    model: str
    name: str
    brand: str
    category: str
    color: str
    size: str
    image: str | None
    net_price: float
    recommended_price: float
