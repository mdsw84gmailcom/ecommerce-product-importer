from datetime import datetime
from pathlib import Path

import pandas as pd

from ecommerce_product_importer.services.dj_snapshot_pipeline import (
    compare_and_snapshot_dj_status,
)


def row(
    *,
    price: float = 100.0,
    statuses: str = "ACTIVE",
    tags: str = "",
) -> dict:
    return {
        "sku": "A-1",
        "product_id": "A",
        "product_name": "Test",
        "color": "Svart",
        "color_code": "04",
        "size": "M",
        "dealer_price": price,
        "recommended_price": 200.0,
        "statuses": statuses,
        "shopify_tags": tags,
    }


def write_report(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def test_first_run_has_no_shopify_plan(tmp_path: Path) -> None:
    current = tmp_path / "current.csv"
    write_report(current, [row()])

    result = compare_and_snapshot_dj_status(
        current,
        snapshot_dir=tmp_path / "snapshots",
        reports_dir=tmp_path / "reports",
        timestamp=datetime(2026, 10, 18, 15, 0, 0),
    )

    assert result.shopify_dry_run_report is None
    assert result.shopify_plan_count == 0
    assert result.shopify_auto_apply_eligible_count == 0


def test_second_run_creates_shopify_dry_run_plan(tmp_path: Path) -> None:
    snapshot_dir = tmp_path / "snapshots"
    reports_dir = tmp_path / "reports"

    first = tmp_path / "first.csv"
    write_report(first, [row()])
    compare_and_snapshot_dj_status(
        first,
        snapshot_dir=snapshot_dir,
        reports_dir=reports_dir,
        timestamp=datetime(2026, 10, 18, 15, 0, 0),
    )

    second = tmp_path / "second.csv"
    write_report(second, [row(price=120.0)])
    result = compare_and_snapshot_dj_status(
        second,
        snapshot_dir=snapshot_dir,
        reports_dir=reports_dir,
        timestamp=datetime(2026, 10, 19, 15, 0, 0),
    )

    assert result.shopify_dry_run_report is not None
    assert result.shopify_dry_run_report.exists()
    assert result.shopify_plan_count == 1
    assert result.shopify_auto_apply_eligible_count == 0

    plan = pd.read_csv(result.shopify_dry_run_report)
    assert list(plan["action"]) == ["REVIEW_PRICE_UPDATE"]


def test_lifecycle_tag_change_counts_as_auto_apply_eligible(
    tmp_path: Path,
) -> None:
    snapshot_dir = tmp_path / "snapshots"
    reports_dir = tmp_path / "reports"

    first = tmp_path / "first.csv"
    write_report(first, [row()])
    compare_and_snapshot_dj_status(
        first,
        snapshot_dir=snapshot_dir,
        reports_dir=reports_dir,
        timestamp=datetime(2026, 10, 18, 15, 0, 0),
    )

    second = tmp_path / "second.csv"
    write_report(second, [row(statuses="SALE", tags="sale")])
    result = compare_and_snapshot_dj_status(
        second,
        snapshot_dir=snapshot_dir,
        reports_dir=reports_dir,
        timestamp=datetime(2026, 10, 19, 15, 0, 0),
    )

    assert result.shopify_plan_count == 2
    assert result.shopify_auto_apply_eligible_count == 1
