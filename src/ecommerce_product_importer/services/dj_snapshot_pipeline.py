from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd

from ecommerce_product_importer.services.dj_change_report import (
    compare_dj_status_reports,
    save_dj_change_report,
)
from ecommerce_product_importer.services.dj_entity_changes import (
    compare_dj_product_color_changes,
    save_dj_product_color_changes,
)
from ecommerce_product_importer.services.dj_shopify_plan import (
    build_dj_shopify_dry_run_plan,
    save_dj_shopify_dry_run_plan,
)
from ecommerce_product_importer.services.dj_snapshots import (
    create_dj_status_snapshot,
    list_dj_status_snapshots,
)


@dataclass(frozen=True)
class DJSnapshotComparisonResult:
    previous_snapshot: Path | None
    current_snapshot: Path
    sku_change_report: Path | None
    entity_change_report: Path | None
    shopify_dry_run_report: Path | None
    sku_change_count: int
    entity_change_count: int
    shopify_plan_count: int
    shopify_auto_apply_eligible_count: int


def compare_and_snapshot_dj_status(
    current_report: Path,
    *,
    snapshot_dir: Path = Path("data/dj/snapshots"),
    reports_dir: Path = Path("data/dj/reports"),
    timestamp: datetime | None = None,
) -> DJSnapshotComparisonResult:
    """
    Compare the current D&J status report with the latest prior snapshot,
    save review reports, and finally preserve the current report as a snapshot.

    On the first run there is no comparison; the current report becomes the
    baseline snapshot.
    """
    if not current_report.exists():
        raise FileNotFoundError(current_report)

    snapshots = list_dj_status_snapshots(snapshot_dir)
    previous_snapshot = snapshots[-1] if snapshots else None

    sku_report_path: Path | None = None
    entity_report_path: Path | None = None
    shopify_plan_path: Path | None = None
    sku_count = 0
    entity_count = 0
    shopify_plan_count = 0
    auto_apply_count = 0

    if previous_snapshot is not None:
        previous = pd.read_csv(previous_snapshot, dtype={"sku": "string"})
        current = pd.read_csv(current_report, dtype={"sku": "string"})

        sku_changes = compare_dj_status_reports(previous, current)
        entity_changes = compare_dj_product_color_changes(
            previous.astype("string"),
            current.astype("string"),
        )

        reports_dir.mkdir(parents=True, exist_ok=True)
        sku_report_path = reports_dir / "dj_change_report.csv"
        entity_report_path = reports_dir / "dj_product_color_changes.csv"

        save_dj_change_report(sku_changes, sku_report_path)
        save_dj_product_color_changes(entity_changes, entity_report_path)

        shopify_plan = build_dj_shopify_dry_run_plan(sku_changes)
        shopify_plan_path = reports_dir / "dj_shopify_dry_run.csv"
        save_dj_shopify_dry_run_plan(shopify_plan, shopify_plan_path)

        sku_count = len(sku_changes)
        entity_count = len(entity_changes)
        shopify_plan_count = len(shopify_plan)
        if not shopify_plan.empty:
            auto_apply_count = int(
                shopify_plan["auto_apply_allowed"].fillna(False).sum()
            )

    current_snapshot = create_dj_status_snapshot(
        current_report,
        snapshot_dir,
        timestamp=timestamp,
    )

    return DJSnapshotComparisonResult(
        previous_snapshot=previous_snapshot,
        current_snapshot=current_snapshot,
        sku_change_report=sku_report_path,
        entity_change_report=entity_report_path,
        shopify_dry_run_report=shopify_plan_path,
        sku_change_count=sku_count,
        entity_change_count=entity_count,
        shopify_plan_count=shopify_plan_count,
        shopify_auto_apply_eligible_count=auto_apply_count,
    )
