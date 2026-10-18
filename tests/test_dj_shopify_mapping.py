from datetime import date
from pathlib import Path

from ecommerce_product_importer.readers.dj_reader import DJProductRow
from ecommerce_product_importer.services.dj_lifecycle import evaluate_dj_rows
from ecommerce_product_importer.services.dj_shopify_mapping import (
    build_dj_shopify_preview,
    save_dj_shopify_preview,
)


def product_row(**overrides) -> DJProductRow:
    values = {
        "supplier": "D&J",
        "product_id": "410000",
        "product_name": "Testprodukt",
        "brand": "Queen Anne",
        "category": "Kök;Test",
        "description": "Beskrivning",
        "image_urls": (
            "https://example.com/1.jpg",
            "https://example.com/2.jpg",
        ),
        "main_image": "https://example.com/1.jpg",
        "recommended_price": 499.0,
        "dealer_price": 199.0,
        "gender": "Unisex",
        "fit": None,
        "material_technique": "rPET",
        "season": "AW26",
        "tags": ("New",),
        "packaging_comment": None,
        "presentation_date": date(2026, 9, 1),
        "color": "Svart",
        "color_code": "99",
        "sku": "410000-99-0",
        "size_code": "0",
        "size_name": "One Size",
        "ean": "7393533000000",
        "available_from": date(2026, 10, 1),
    }
    values.update(overrides)
    return DJProductRow(**values)


def test_build_preview_maps_shopify_fields() -> None:
    evaluated = evaluate_dj_rows(
        [product_row()],
        today=date(2026, 10, 18),
    )

    preview = build_dj_shopify_preview(evaluated)
    row = preview.iloc[0]

    assert row["Handle"] == "dj-410000"
    assert row["Title"] == "Testprodukt"
    assert row["Vendor"] == "Queen Anne"
    assert row["Option1 Name"] == "Färg"
    assert row["Option1 Value"] == "Svart"
    assert row["Option2 Name"] == "Storlek"
    assert row["Option2 Value"] == "One Size"
    assert row["Variant SKU"] == "410000-99-0"
    assert row["Variant Barcode"] == "7393533000000"
    assert row["Tags"] == "new"


def test_price_is_not_assumed() -> None:
    evaluated = evaluate_dj_rows(
        [product_row()],
        today=date(2026, 10, 18),
    )

    preview = build_dj_shopify_preview(evaluated)
    row = preview.iloc[0]

    assert row["Supplier Dealer Price"] == 199.0
    assert row["Supplier Recommended Price"] == 499.0
    assert row["Shopify Price"] is None
    assert row["Price Status"] == "REVIEW_REQUIRED"


def test_images_are_unique_and_main_image_first() -> None:
    evaluated = evaluate_dj_rows(
        [product_row()],
        today=date(2026, 10, 18),
    )

    preview = build_dj_shopify_preview(evaluated)

    assert preview.iloc[0]["Image URLs"] == (
        "https://example.com/1.jpg;"
        "https://example.com/2.jpg"
    )


def test_save_preview(tmp_path: Path) -> None:
    evaluated = evaluate_dj_rows(
        [product_row()],
        today=date(2026, 10, 18),
    )
    output = tmp_path / "preview.csv"

    dataframe = save_dj_shopify_preview(evaluated, output)

    assert output.exists()
    assert len(dataframe) == 1
