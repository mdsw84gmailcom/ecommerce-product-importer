from pathlib import Path

import pandas as pd
import pytest

from ecommerce_product_importer.services.dj_shopify_plan import (
    build_dj_shopify_dry_run_plan,
    save_dj_shopify_dry_run_plan,
    summarize_dj_shopify_plan,
)


def change_row(change_type: str, **overrides) -> dict:
    row = {
        "change_type": change_type,
        "sku": "A-1",
        "product_id": "A",
        "product_name": "Test",
        "old_dealer_price": 100.0,
        "new_dealer_price": 110.0,
        "old_recommended_price": 200.0,
        "new_recommended_price": 220.0,
        "old_statuses": "ACTIVE",
        "new_statuses": "SALE",
        "old_shopify_tags": "",
        "new_shopify_tags": "sale",
    }
    row.update(overrides)
    return row


def test_new_sku_requires_review() -> None:
    plan = build_dj_shopify_dry_run_plan(
        pd.DataFrame([change_row("NEW_SKU")])
    )

    assert plan.iloc[0]["action"] == "CREATE_OR_REVIEW_VARIANT"
    assert bool(plan.iloc[0]["auto_apply_allowed"]) is False


def test_removed_sku_is_never_auto_applied() -> None:
    plan = build_dj_shopify_dry_run_plan(
        pd.DataFrame([change_row("REMOVED_SKU")])
    )

    assert plan.iloc[0]["action"] == "REVIEW_REMOVAL"
    assert plan.iloc[0]["risk"] == "HIGH"
    assert bool(plan.iloc[0]["auto_apply_allowed"]) is False


def test_price_change_requires_review() -> None:
    plan = build_dj_shopify_dry_run_plan(
        pd.DataFrame([change_row("PRICE_CHANGED")])
    )

    assert plan.iloc[0]["action"] == "REVIEW_PRICE_UPDATE"
    assert plan.iloc[0]["risk"] == "HIGH"
    assert bool(plan.iloc[0]["auto_apply_allowed"]) is False


def test_lifecycle_tag_change_can_be_auto_apply_eligible() -> None:
    plan = build_dj_shopify_dry_run_plan(
        pd.DataFrame(
            [
                change_row(
                    "SHOPIFY_TAGS_CHANGED",
                    old_shopify_tags="",
                    new_shopify_tags="sale",
                )
            ]
        )
    )

    assert plan.iloc[0]["action"] == "UPDATE_LIFECYCLE_TAGS"
    assert plan.iloc[0]["risk"] == "LOW"
    assert bool(plan.iloc[0]["auto_apply_allowed"]) is True


def test_unknown_change_is_safe_by_default() -> None:
    plan = build_dj_shopify_dry_run_plan(
        pd.DataFrame([change_row("SOMETHING_NEW")])
    )

    assert plan.iloc[0]["action"] == "REVIEW_UNKNOWN_CHANGE"
    assert bool(plan.iloc[0]["auto_apply_allowed"]) is False


def test_missing_columns_are_rejected() -> None:
    with pytest.raises(ValueError, match="Missing required"):
        build_dj_shopify_dry_run_plan(
            pd.DataFrame([{"change_type": "NEW_SKU"}])
        )


def test_summary_and_save(tmp_path: Path) -> None:
    changes = pd.DataFrame(
        [
            change_row("NEW_SKU", sku="A"),
            change_row("PRICE_CHANGED", sku="B"),
            change_row("SHOPIFY_TAGS_CHANGED", sku="C"),
        ]
    )
    plan = build_dj_shopify_dry_run_plan(changes)

    assert summarize_dj_shopify_plan(plan) == {
        "CREATE_OR_REVIEW_VARIANT": 1,
        "REVIEW_PRICE_UPDATE": 1,
        "UPDATE_LIFECYCLE_TAGS": 1,
    }

    output = tmp_path / "plan.csv"
    save_dj_shopify_dry_run_plan(plan, output)
    assert output.exists()
