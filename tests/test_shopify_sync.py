import pandas as pd

from ecommerce_product_importer.services.shopify_sync import (
    build_change_plan,
    build_product_update_payloads,
    compare_products,
    compare_variants,
    update_products,
)


def make_live_variant():
    return pd.DataFrame(
        [
            {
                "variant_sku": "100001",
                "price": "100.00",
                "barcode": "123456789",
                "color": "Svart",
                "size": "M",
            }
        ]
    )


def make_new_variant():
    return pd.DataFrame(
        [
            {
                "Variant SKU": "100001",
                "Variant Price": 100.00,
                "Variant Barcode": "123456789",
                "Option1 Value": "Svart",
                "Option2 Value": "M",
            }
        ]
    )


def test_variant_unchanged():
    result = compare_variants(
        make_live_variant(),
        make_new_variant(),
    )

    assert result.iloc[0]["status"] == "UNCHANGED"


def test_variant_updated():
    new = make_new_variant()
    new.loc[0, "Variant Price"] = 120.00

    result = compare_variants(
        make_live_variant(),
        new,
    )

    assert result.iloc[0]["status"] == "UPDATED"


def test_variant_new():
    live = make_live_variant().iloc[0:0]

    result = compare_variants(
        live,
        make_new_variant(),
    )

    assert result.iloc[0]["status"] == "NEW"


def test_variant_discontinued():
    new = make_new_variant().iloc[0:0]

    result = compare_variants(
        make_live_variant(),
        new,
    )

    assert result.iloc[0]["status"] == "DISCONTINUED"


def test_product_unchanged():
    live = pd.DataFrame(
        [
            {
                "shopify_product_id": "gid://shopify/Product/123",
                "handle": "snickers-1100",
                "title": "Test product",
                "description_html": "<p>Description</p>",
            }
        ]
    )

    new = pd.DataFrame(
        [
            {
                "Handle": "snickers-1100",
                "Title": "Test product",
                "Body (HTML)": "<p>Description</p>",
            }
        ]
    )

    result = compare_products(live, new)

    assert result.iloc[0]["status"] == "UNCHANGED"


def test_product_updated():
    live = pd.DataFrame(
        [
            {
                "shopify_product_id": "gid://shopify/Product/123",
                "handle": "snickers-1100",
                "title": "Test product",
                "description_html": "<p>Old description</p>",
            }
        ]
    )

    new = pd.DataFrame(
        [
            {
                "Handle": "snickers-1100",
                "Title": "Test product",
                "Body (HTML)": "<p>New description</p>",
            }
        ]
    )

    result = compare_products(live, new)

    assert result.iloc[0]["status"] == "UPDATED"


def test_change_plan():
    variant_comparison = pd.DataFrame(
        {
            "status": [
                "NEW",
                "UPDATED",
                "DISCONTINUED",
                "UNCHANGED",
            ]
        }
    )

    product_comparison = pd.DataFrame(
        {
            "status": [
                "UPDATED",
                "UNCHANGED",
            ]
        }
    )

    plan = build_change_plan(
        variant_comparison,
        product_comparison,
    )

    assert len(plan["variants_new"]) == 1
    assert len(plan["variants_updated"]) == 1
    assert len(plan["variants_discontinued"]) == 1

    assert len(plan["products_new"]) == 0
    assert len(plan["products_updated"]) == 1
    assert len(plan["products_discontinued"]) == 0


def test_build_product_update_payloads():
    comparison = pd.DataFrame(
        [
            {
                "shopify_product_id": "gid://shopify/Product/123",
                "new_title": "Updated product",
                "new_description": "<p>Updated description</p>",
                "status": "UPDATED",
            },
            {
                "shopify_product_id": "gid://shopify/Product/456",
                "new_title": "Unchanged product",
                "new_description": "<p>Description</p>",
                "status": "UNCHANGED",
            },
        ]
    )

    payloads = build_product_update_payloads(comparison)

    assert payloads == [
        {
            "id": "gid://shopify/Product/123",
            "title": "Updated product",
            "descriptionHtml": "<p>Updated description</p>",
        }
    ]


def test_update_products_dry_run():
    payloads = [
        {
            "id": "gid://shopify/Product/123",
            "title": "Updated product",
            "descriptionHtml": "<p>Updated description</p>",
        }
    ]

    results = update_products(
        shop="example.myshopify.com",
        access_token="fake-token",
        payloads=payloads,
    )

    assert results == [
        {
            "status": "DRY_RUN",
            "payload": payloads[0],
        }
    ]


def test_update_products_with_mock(monkeypatch):
    payloads = [
        {
            "id": "gid://shopify/Product/123",
            "title": "Updated product",
            "descriptionHtml": "<p>Updated description</p>",
        }
    ]

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "data": {
                    "productUpdate": {
                        "product": {
                            "id": "gid://shopify/Product/123",
                            "title": "Updated product",
                        },
                        "userErrors": [],
                    }
                }
            }

    def mock_post(*args, **kwargs):
        return MockResponse()

    monkeypatch.setattr(
        "ecommerce_product_importer.services.shopify_sync.requests.post",
        mock_post,
    )

    results = update_products(
        shop="example.myshopify.com",
        access_token="fake-token",
        payloads=payloads,
        dry_run=False,
    )

    assert results[0]["status"] == "UPDATED"
    assert results[0]["product"]["id"] == "gid://shopify/Product/123"
