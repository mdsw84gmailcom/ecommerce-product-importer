from dataclasses import dataclass


@dataclass
class Product:
    model: str
    name: str
    brand: str
    category: str
