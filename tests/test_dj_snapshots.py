from datetime import datetime
from pathlib import Path

from ecommerce_product_importer.services.dj_snapshots import (
    create_dj_status_snapshot,
    list_dj_status_snapshots,
)


def test_create_and_list_snapshot(tmp_path: Path) -> None:
    report = tmp_path / "report.csv"
    report.write_text("sku\nA-1\n", encoding="utf-8")

    snapshot_dir = tmp_path / "snapshots"
    created = create_dj_status_snapshot(
        report,
        snapshot_dir,
        timestamp=datetime(2026, 10, 18, 13, 30, 0),
    )

    assert created.name == "2026-10-18_133000_status.csv"
    assert created.read_text(encoding="utf-8") == "sku\nA-1\n"
    assert list_dj_status_snapshots(snapshot_dir) == [created]
