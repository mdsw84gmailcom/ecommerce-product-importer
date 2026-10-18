from pathlib import Path

from ecommerce_product_importer.readers.dj_reader import DJProductRow
from ecommerce_product_importer.services.dj_business_rules import (
    build_dj_category_review,
    build_dj_price_review,
    save_dj_business_rule_reviews,
)


def row(**overrides) -> DJProductRow:
    values = {
        "supplier": "D&J",
        "product_id": "410000",
        "product_name": "Test",
        "brand": "Queen Anne",
        "category": "Kök",
        "description": "",
        "image_urls": (),
        "main_image": None,
        "recommended_price": 499.0,
        "dealer_price": 199.0,
        "gender": None,
        "fit": None,
        "material_technique": None,
        "season": None,
        "tags": (),
        "packaging_comment": None,
        "presentation_date": None,
        "color": "Svart",
        "color_code": "99",
        "sku": "410000-99-0",
        "size_code": "0",
        "size_name": "One Size",
        "ean": None,
        "available_from": None,
    }
    values.update(overrides)
    return DJProductRow(**values)


def test_category_review_groups_products_and_skus() -> None:
    rows = [
        row(sku="A-1", product_id="A"),
        row(sku="A-2", product_id="A"),
        row(sku="B-1", product_id="B"),
    ]

    review = build_dj_category_review(rows)

    assert len(review) == 1
    assert review.iloc[0]["unique_products"] == 2
    assert review.iloc[0]["sku_rows"] == 3
    assert review.iloc[0]["mapping_status"] == "REVIEW_REQUIRED"


def test_price_review_does_not_calculate_shopify_price() -> None:
    review = build_dj_price_review([row()])

    assert review.iloc[0]["dealer_price"] == 199.0
    assert review.iloc[0]["recommended_price"] == 499.0
    assert review.iloc[0]["recommended_to_dealer_ratio"] == 2.5075
    assert review.iloc[0]["price_rule"] == ""
    assert review.iloc[0]["price_status"] == "REVIEW_REQUIRED"


def test_missing_prices_are_supported() -> None:
    review = build_dj_price_review(
        [row(dealer_price=None, recommended_price=None)]
    )

    assert review.iloc[0]["recommended_to_dealer_ratio"] is None


def test_save_reviews(tmp_path: Path) -> None:
    category_path, price_path = save_dj_business_rule_reviews(
        [row()],
        tmp_path,
    )

    assert category_path.exists()
    assert price_path.exists()
