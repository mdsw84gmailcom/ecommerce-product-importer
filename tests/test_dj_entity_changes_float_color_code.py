import pandas as pd

from ecommerce_product_importer.services.dj_entity_changes import (
    compare_dj_product_color_changes,
)


def row(code: str) -> dict:
    return {
        "product_id": "A",
        "product_name": "Test",
        "color": "Svart",
        "color_code": code,
    }


def test_float_formatted_color_code_is_same_identity() -> None:
    previous = pd.DataFrame([row("04")])
    current = pd.DataFrame([row("4.0")])

    changes = compare_dj_product_color_changes(previous, current)

    assert changes.empty


def test_alphanumeric_color_code_is_preserved_case_insensitively() -> None:
    previous = pd.DataFrame([row("AB04")])
    current = pd.DataFrame([row("ab04")])

    changes = compare_dj_product_color_changes(previous, current)

    assert changes.empty
