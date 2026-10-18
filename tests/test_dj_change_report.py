from pathlib import Path

import pandas as pd
import pytest

from ecommerce_product_importer.services.dj_change_report import (
    compare_dj_status_reports,
    save_dj_change_report,
    summarize_dj_changes,
)


def make_report(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def base_row(**overrides) -> dict:
    row = {
        "sku": "A-1",
        "product_id": "A",
        "product_name": "Test",
        "color": "Svart",
        "size": "M",
        "dealer_price": 100.0,
        "recommended_price": 200.0,
        "statuses": "ACTIVE",
        "shopify_tags": "",
    }
    row.update(overrides)
    return row


def test_new_and_removed_sku() -> None:
    previous = make_report([base_row(sku="OLD")])
    current = make_report([base_row(sku="NEW")])

    changes = compare_dj_status_reports(previous, current)

    assert set(changes["change_type"]) == {"NEW_SKU", "REMOVED_SKU"}


def test_price_change() -> None:
    previous = make_report([base_row()])
    current = make_report([base_row(dealer_price=120.0)])

    changes = compare_dj_status_reports(previous, current)

    assert list(changes["change_type"]) == ["PRICE_CHANGED"]
    assert changes.iloc[0]["old_dealer_price"] == 100.0
    assert changes.iloc[0]["new_dealer_price"] == 120.0


def test_status_and_shopify_tag_change() -> None:
    previous = make_report([base_row(statuses="ACTIVE", shopify_tags="")])
    current = make_report(
        [base_row(statuses="SALE", shopify_tags="sale")]
    )

    changes = compare_dj_status_reports(previous, current)

    assert set(changes["change_type"]) == {
        "STATUS_CHANGED",
        "SHOPIFY_TAGS_CHANGED",
    }


def test_variant_change() -> None:
    previous = make_report([base_row(color="Svart", size="M")])
    current = make_report([base_row(color="Blå", size="L")])

    changes = compare_dj_status_reports(previous, current)

    assert list(changes["change_type"]) == ["VARIANT_CHANGED"]


def test_no_changes_returns_empty_dataframe() -> None:
    previous = make_report([base_row()])
    current = make_report([base_row()])

    changes = compare_dj_status_reports(previous, current)

    assert changes.empty
    assert list(changes.columns)[0] == "change_type"


def test_duplicate_sku_is_rejected() -> None:
    previous = make_report([base_row(), base_row()])
    current = make_report([base_row()])

    with pytest.raises(ValueError, match="Duplicate SKU"):
        compare_dj_status_reports(previous, current)


def test_summary_and_save(tmp_path: Path) -> None:
    changes = pd.DataFrame(
        [
            {"change_type": "NEW_SKU"},
            {"change_type": "NEW_SKU"},
            {"change_type": "PRICE_CHANGED"},
        ]
    )

    assert summarize_dj_changes(changes) == {
        "NEW_SKU": 2,
        "PRICE_CHANGED": 1,
    }

    output = tmp_path / "changes.csv"
    save_dj_change_report(changes, output)
    assert output.exists()
