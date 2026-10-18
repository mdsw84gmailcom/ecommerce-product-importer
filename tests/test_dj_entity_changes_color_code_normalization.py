import pandas as pd

from ecommerce_product_importer.services.dj_entity_changes import (
    compare_dj_product_color_changes,
)


def row(product_id: str, color: str, color_code: str) -> dict:
    return {
        "product_id": product_id,
        "product_name": "Test",
        "color": color,
        "color_code": color_code,
    }


def test_numeric_color_code_leading_zero_is_same_identity() -> None:
    previous = pd.DataFrame([row("A", "Svart", "04")])
    current = pd.DataFrame([row("A", "Svart", "4")])

    changes = compare_dj_product_color_changes(previous, current)

    assert changes.empty
