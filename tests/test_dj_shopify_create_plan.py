import pandas as pd
import pytest

from ecommerce_product_importer.services.dj_shopify_create_plan import (
    build_dj_create_plans,
    validate_dj_create_preview,
)


def preview() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Handle": "dj-410001",
                "Title": "Frotté 420g",
                "Body (HTML)": "Beskrivning",
                "Vendor": "Queen Anne",
                "Tags": "new",
                "Option1 Value": "Vit",
                "Option2 Value": "30x50",
                "Variant SKU": "410001-00-04",
                "Variant Barcode": "7390000000001",
                "Shopify Price": 48.75,
                "Price Status": "READY",
                "Image URLs": "https://example.com/1.jpg;https://example.com/2.jpg",
                "Suggested Collection": "Handdukar & frotté",
                "Collection Mapping Status": "SUGGESTED",
            },
            {
                "Handle": "dj-410001",
                "Title": "Frotté 420g",
                "Body (HTML)": "Beskrivning",
                "Vendor": "Queen Anne",
                "Tags": "new,sale",
                "Option1 Value": "Vit",
                "Option2 Value": "50x70",
                "Variant SKU": "410001-00-06",
                "Variant Barcode": "7390000000002",
                "Shopify Price": 73.75,
                "Price Status": "READY",
                "Image URLs": "https://example.com/1.jpg;https://example.com/3.jpg",
                "Suggested Collection": "Handdukar & frotté",
                "Collection Mapping Status": "SUGGESTED",
            },
        ]
    )


def test_build_create_plan_groups_variants_per_product() -> None:
    plans = build_dj_create_plans(preview(), {"dj-410001"})

    assert len(plans) == 1
    plan = plans[0]

    assert plan.product_create["status"] == "DRAFT"
    assert plan.product_create["handle"] == "dj-410001"
    assert plan.product_create["tags"] == ["new", "sale"]
    assert plan.product_create["productOptions"] == [
        {"name": "Färg", "values": [{"name": "Vit"}]},
        {
            "name": "Storlek",
            "values": [{"name": "30x50"}, {"name": "50x70"}],
        },
    ]
    assert plan.initial_variant["price"] == "48.75"
    assert plan.initial_variant["inventoryItem"]["sku"] == "410001-00-04"
    assert len(plan.additional_variants) == 1
    assert plan.additional_variants[0]["price"] == "73.75"
    assert plan.additional_variants[0]["inventoryItem"]["sku"] == "410001-00-06"


def test_plan_keeps_images_unique_and_collection_as_review_metadata() -> None:
    plan = build_dj_create_plans(preview(), {"dj-410001"})[0]

    assert plan.image_urls == [
        "https://example.com/1.jpg",
        "https://example.com/2.jpg",
        "https://example.com/3.jpg",
    ]
    assert plan.suggested_collection == "Handdukar & frotté"
    assert plan.collection_mapping_status == "SUGGESTED"


def test_only_new_handles_are_planned() -> None:
    assert build_dj_create_plans(preview(), set()) == []


def test_missing_price_blocks_create_plan() -> None:
    data = preview()
    data.loc[0, "Shopify Price"] = None

    errors = validate_dj_create_preview(data)

    assert any("missing Shopify Price" in error for error in errors)

    with pytest.raises(ValueError, match="validation failed"):
        build_dj_create_plans(data, {"dj-410001"})


def test_partially_blank_variant_option_blocks_create_plan() -> None:
    data = preview()
    data.loc[0, "Option2 Value"] = ""

    errors = validate_dj_create_preview(data)

    assert any("partially blank Option2 Value" in error for error in errors)


def test_product_without_color_uses_only_size_option() -> None:
    data = preview()
    data["Option1 Value"] = ""

    plan = build_dj_create_plans(data, {"dj-410001"})[0]

    assert plan.product_create["productOptions"] == [
        {
            "name": "Storlek",
            "values": [{"name": "30x50"}, {"name": "50x70"}],
        }
    ]
    assert plan.initial_variant["optionValues"] == [
        {"optionName": "Storlek", "name": "30x50"}
    ]


def test_one_size_product_without_color_is_allowed() -> None:
    data = preview().iloc[[0]].copy()
    data.loc[:, "Option1 Value"] = ""
    data.loc[:, "Option2 Value"] = "One Size"

    plan = build_dj_create_plans(data, {"dj-410001"})[0]

    assert plan.product_create["productOptions"] == [
        {"name": "Storlek", "values": [{"name": "One Size"}]}
    ]
    assert plan.initial_variant["optionValues"] == [
        {"optionName": "Storlek", "name": "One Size"}
    ]
