import pytest

from ecommerce_product_importer.services.dj_shopify_executor import (
    _resolve_runtime_variables,
    execute_dj_product_create,
)
from ecommerce_product_importer.services.dj_shopify_mutation_plan import (
    DJMutationOperation,
)


def operations(status="DRAFT"):
    return [
        DJMutationOperation(
            handle="dj-410001",
            step=1,
            mutation_name="productCreate",
            query="mutation ProductCreate { productCreate { userErrors { message } } }",
            variables={
                "product": {
                    "handle": "dj-410001",
                    "status": status,
                },
                "media": [],
            },
        ),
        DJMutationOperation(
            handle="dj-410001",
            step=2,
            mutation_name="productVariantsBulkUpdate",
            query="mutation Update { productVariantsBulkUpdate { userErrors { message } } }",
            variables={
                "productId": "$PRODUCT_ID",
                "variants": [
                    {
                        "id": "$INITIAL_VARIANT_ID",
                        "price": "48.75",
                    }
                ],
            },
        ),
    ]


def test_dry_run_performs_no_network_write(monkeypatch) -> None:
    def fail_post(*args, **kwargs):
        raise AssertionError("network write should not happen in dry-run")

    monkeypatch.setattr("requests.post", fail_post)

    result = execute_dj_product_create(
        shop="example.myshopify.com",
        access_token="token",
        operations=operations(),
        handle="dj-410001",
    )

    assert result.status == "DRY_RUN"
    assert result.completed_mutations == ()
    assert result.product_id is None


def test_non_draft_product_is_blocked() -> None:
    with pytest.raises(ValueError, match="DRAFT"):
        execute_dj_product_create(
            shop="example.myshopify.com",
            access_token="token",
            operations=operations(status="ACTIVE"),
            handle="dj-410001",
        )


def test_delete_or_publish_mutations_are_blocked() -> None:
    unsafe = operations() + [
        DJMutationOperation(
            handle="dj-410001",
            step=3,
            mutation_name="publishablePublish",
            query="mutation Publish { publishablePublish { userErrors { message } } }",
            variables={},
        )
    ]

    with pytest.raises(ValueError, match="Delete/publish"):
        execute_dj_product_create(
            shop="example.myshopify.com",
            access_token="token",
            operations=unsafe,
            handle="dj-410001",
        )


def test_runtime_placeholders_are_resolved() -> None:
    resolved = _resolve_runtime_variables(
        {
            "productId": "$PRODUCT_ID",
            "variants": [{"id": "$INITIAL_VARIANT_ID"}],
        },
        product_id="gid://shopify/Product/1",
        initial_variant_id="gid://shopify/ProductVariant/2",
    )

    assert resolved == {
        "productId": "gid://shopify/Product/1",
        "variants": [{"id": "gid://shopify/ProductVariant/2"}],
    }


def test_apply_executes_create_then_update(monkeypatch) -> None:
    responses = iter(
        [
            {
                "data": {
                    "productCreate": {
                        "product": {
                            "id": "gid://shopify/Product/1",
                            "status": "DRAFT",
                            "variants": {
                                "nodes": [
                                    {"id": "gid://shopify/ProductVariant/2"}
                                ]
                            },
                        },
                        "userErrors": [],
                    }
                }
            },
            {
                "data": {
                    "productVariantsBulkUpdate": {
                        "productVariants": [
                            {"id": "gid://shopify/ProductVariant/2"}
                        ],
                        "userErrors": [],
                    }
                }
            },
        ]
    )

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    seen_variables = []

    def fake_post(url, headers, json, timeout):
        seen_variables.append(json["variables"])
        return Response(next(responses))

    monkeypatch.setattr("requests.post", fake_post)

    result = execute_dj_product_create(
        shop="example.myshopify.com",
        access_token="token",
        operations=operations(),
        handle="dj-410001",
        apply=True,
    )

    assert result.status == "CREATED_DRAFT"
    assert result.product_id == "gid://shopify/Product/1"
    assert result.initial_variant_id == "gid://shopify/ProductVariant/2"
    assert result.completed_mutations == (
        "productCreate",
        "productVariantsBulkUpdate",
    )
    assert seen_variables[1]["productId"] == "gid://shopify/Product/1"
    assert seen_variables[1]["variants"][0]["id"] == (
        "gid://shopify/ProductVariant/2"
    )
