from ecommerce_product_importer.services.dj_shopify_create_plan import (
    DJCreatePlan,
)
from ecommerce_product_importer.services.dj_shopify_mutation_plan import (
    build_dj_mutation_plan,
    summarize_mutation_plan,
)


def create_plan(additional_variants=True) -> DJCreatePlan:
    return DJCreatePlan(
        handle="dj-410001",
        product_create={
            "title": "Frotté 420g",
            "handle": "dj-410001",
            "status": "DRAFT",
            "productOptions": [
                {"name": "Färg", "values": [{"name": "Vit"}]},
                {
                    "name": "Storlek",
                    "values": [
                        {"name": "30x50"},
                        {"name": "50x70"},
                    ],
                },
            ],
        },
        initial_variant={
            "price": "48.75",
            "inventoryItem": {
                "sku": "410001-00-04",
                "tracked": False,
            },
            "taxable": True,
            "optionValues": [
                {"optionName": "Färg", "name": "Vit"},
                {"optionName": "Storlek", "name": "30x50"},
            ],
            "barcode": "7390000000001",
        },
        additional_variants=(
            [
                {
                    "price": "73.75",
                    "inventoryItem": {
                        "sku": "410001-00-06",
                        "tracked": False,
                    },
                    "taxable": True,
                    "optionValues": [
                        {"optionName": "Färg", "name": "Vit"},
                        {"optionName": "Storlek", "name": "50x70"},
                    ],
                    "barcode": "7390000000002",
                }
            ]
            if additional_variants
            else []
        ),
        suggested_collection="Handdukar & frotté",
        collection_mapping_status="SUGGESTED",
        image_urls=["https://example.com/1.jpg"],
    )


def test_mutation_plan_is_ordered_and_uses_runtime_placeholders() -> None:
    operations = build_dj_mutation_plan([create_plan()])

    assert [operation.mutation_name for operation in operations] == [
        "productCreate",
        "productVariantsBulkUpdate",
        "productVariantsBulkCreate",
    ]

    assert operations[0].variables["product"]["status"] == "DRAFT"

    update = operations[1]
    assert update.variables["productId"] == "$PRODUCT_ID"
    assert update.variables["variants"][0]["id"] == "$INITIAL_VARIANT_ID"
    assert update.variables["variants"][0]["price"] == "48.75"

    create = operations[2]
    assert create.variables["productId"] == "$PRODUCT_ID"
    assert create.variables["variants"][0]["inventoryItem"]["sku"] == (
        "410001-00-06"
    )


def test_single_variant_product_has_no_bulk_create_operation() -> None:
    operations = build_dj_mutation_plan(
        [create_plan(additional_variants=False)]
    )

    assert [operation.mutation_name for operation in operations] == [
        "productCreate",
        "productVariantsBulkUpdate",
    ]


def test_summary_counts_mutations() -> None:
    operations = build_dj_mutation_plan(
        [
            create_plan(),
            create_plan(additional_variants=False),
        ]
    )

    summary = summarize_mutation_plan(operations)

    assert summary == {
        "productCreate": 2,
        "productVariantsBulkUpdate": 2,
        "productVariantsBulkCreate": 1,
    }


def test_plan_contains_no_delete_or_publish_mutations() -> None:
    operations = build_dj_mutation_plan([create_plan()])

    mutation_names = {operation.mutation_name for operation in operations}

    assert all("Delete" not in name for name in mutation_names)
    assert all("Publish" not in name for name in mutation_names)
