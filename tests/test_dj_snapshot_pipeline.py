from datetime import datetime
from pathlib import Path

import pandas as pd

from ecommerce_product_importer.services.dj_snapshot_pipeline import (
    compare_and_snapshot_dj_status,
)


def report_row(
    sku: str = "A-1",
    *,
    dealer_price: float = 100.0,
    color: str = "Svart",
    color_code: str = "04",
) -> dict:
    return {
        "sku": sku,
        "product_id": "A",
        "product_name": "Test",
        "color": color,
        "color_code": color_code,
        "size": "M",
        "dealer_price": dealer_price,
        "recommended_price": 200.0,
        "statuses": "ACTIVE",
        "shopify_tags": "",
    }


def write_report(path: Path, rows: list[dict]) -> None:
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def test_first_run_creates_baseline_without_change_reports(
    tmp_path: Path,
) -> None:
    current = tmp_path / "current.csv"
    write_report(current, [report_row()])

    result = compare_and_snapshot_dj_status(
        current,
        snapshot_dir=tmp_path / "snapshots",
        reports_dir=tmp_path / "reports",
        timestamp=datetime(2026, 10, 18, 14, 0, 0),
    )

    assert result.previous_snapshot is None
    assert result.current_snapshot.exists()
    assert result.sku_change_report is None
    assert result.entity_change_report is None
    assert result.sku_change_count == 0
    assert result.entity_change_count == 0


def test_second_run_uses_latest_snapshot_and_saves_reports(
    tmp_path: Path,
) -> None:
    snapshot_dir = tmp_path / "snapshots"
    reports_dir = tmp_path / "reports"
    first = tmp_path / "first.csv"
    second = tmp_path / "second.csv"

    write_report(first, [report_row()])
    compare_and_snapshot_dj_status(
        first,
        snapshot_dir=snapshot_dir,
        reports_dir=reports_dir,
        timestamp=datetime(2026, 10, 18, 14, 0, 0),
    )

    write_report(second, [report_row(dealer_price=120.0)])
    result = compare_and_snapshot_dj_status(
        second,
        snapshot_dir=snapshot_dir,
        reports_dir=reports_dir,
        timestamp=datetime(2026, 10, 19, 14, 0, 0),
    )

    assert result.previous_snapshot is not None
    assert result.previous_snapshot.name == "2026-10-18_140000_status.csv"
    assert result.current_snapshot.name == "2026-10-19_140000_status.csv"
    assert result.sku_change_report is not None
    assert result.sku_change_report.exists()
    assert result.entity_change_report is not None
    assert result.entity_change_report.exists()
    assert result.sku_change_count == 1
    assert result.entity_change_count == 0


def test_latest_snapshot_is_selected(tmp_path: Path) -> None:
    snapshot_dir = tmp_path / "snapshots"
    reports_dir = tmp_path / "reports"

    for day, price in [(18, 100.0), (19, 110.0)]:
        report = tmp_path / f"day-{day}.csv"
        write_report(report, [report_row(dealer_price=price)])
        compare_and_snapshot_dj_status(
            report,
            snapshot_dir=snapshot_dir,
            reports_dir=reports_dir,
            timestamp=datetime(2026, 10, day, 14, 0, 0),
        )

    current = tmp_path / "current.csv"
    write_report(current, [report_row(dealer_price=120.0)])
    result = compare_and_snapshot_dj_status(
        current,
        snapshot_dir=snapshot_dir,
        reports_dir=reports_dir,
        timestamp=datetime(2026, 10, 20, 14, 0, 0),
    )

    assert result.previous_snapshot is not None
    assert result.previous_snapshot.name == "2026-10-19_140000_status.csv"
    assert result.sku_change_count == 1
