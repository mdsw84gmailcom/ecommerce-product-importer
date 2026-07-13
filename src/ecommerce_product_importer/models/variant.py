from dataclasses import dataclass


@dataclass
class Variant:
    article_number: str
    model: str
    color: str
    size: str
    image: str | None = None
