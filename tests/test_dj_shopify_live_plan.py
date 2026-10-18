import pandas as pd

from ecommerce_product_importer.services.dj_shopify_live_plan import (
    build_dj_live_dry_run_plan,
)


def preview() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Handle": "dj-410001",
                "Title": "Frotté 420g",
                "Body (HTML)": "Beskrivning",
                "Variant SKU": "410001-00-04",
                "Variant Barcode": "7390000000001",
                "Option1 Value": "Vit",
                "Option2 Value": "30x50",
                "Shopify Price": 48.75,
            }
        ]
    )


def test_first_dj_import_is_new_when_store_has_no_dj_products() -> None:
    unrelated_product = {
        "id": "gid://shopify/Product/1",
        "title": "Snickers product",
        "handle": "snickers-1100",
        "descriptionHtml": "Existing",
        "variants": {
            "nodes": [
                {
                    "id": "gid://shopify/ProductVariant/1",
                    "sku": "SN-1",
                    "barcode": "123",
                    "price": "99.00",
                    "selectedOptions": [
                        {"name": "Färg", "value": "Svart"},
                        {"name": "Storlek", "value": "M"},
                    ],
                }
            ]
        },
    }

    variants, products, plan = build_dj_live_dry_run_plan(
        [unrelated_product],
        preview(),
    )

    assert len(plan["variants_new"]) == 1
    assert len(plan["products_new"]) == 1
    assert len(plan["variants_discontinued"]) == 0
    assert len(plan["products_discontinued"]) == 0
    assert variants.iloc[0]["status"] == "NEW"
    assert products.iloc[0]["status"] == "NEW"


def test_existing_matching_dj_variant_is_unchanged() -> None:
    live_dj = {
        "id": "gid://shopify/Product/2",
        "title": "Frotté 420g",
        "handle": "dj-410001",
        "descriptionHtml": "Beskrivning",
        "variants": {
            "nodes": [
                {
                    "id": "gid://shopify/ProductVariant/2",
                    "sku": "410001-00-04",
                    "barcode": "7390000000001",
                    "price": "48.75",
                    "selectedOptions": [
                        {"name": "Färg", "value": "Vit"},
                        {"name": "Storlek", "value": "30x50"},
                    ],
                }
            ]
        },
    }

    variants, products, plan = build_dj_live_dry_run_plan(
        [live_dj],
        preview(),
    )

    assert variants.iloc[0]["status"] == "UNCHANGED"
    assert products.iloc[0]["status"] == "UNCHANGED"
    assert len(plan["variants_new"]) == 0
    assert len(plan["variants_updated"]) == 0


def test_unrelated_products_are_never_marked_discontinued() -> None:
    unrelated_product = {
        "id": "gid://shopify/Product/3",
        "title": "Other supplier",
        "handle": "other-123",
        "descriptionHtml": "Existing",
        "variants": {
            "nodes": [
                {
                    "id": "gid://shopify/ProductVariant/3",
                    "sku": "OTHER-1",
                    "barcode": None,
                    "price": "10.00",
                    "selectedOptions": [],
                }
            ]
        },
    }

    _, _, plan = build_dj_live_dry_run_plan(
        [unrelated_product],
        preview(),
    )

    assert len(plan["variants_discontinued"]) == 0
    assert len(plan["products_discontinued"]) == 0
