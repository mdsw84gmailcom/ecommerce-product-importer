from argparse import ArgumentParser
from datetime import date
from pathlib import Path

from ecommerce_product_importer.readers.dj_reader import read_dj_export
from ecommerce_product_importer.services.dj_lifecycle import evaluate_dj_rows
from ecommerce_product_importer.services.dj_report import (
    save_dj_status_report,
    summarize_dj_statuses,
)
from ecommerce_product_importer.services.dj_snapshot_pipeline import (
    compare_and_snapshot_dj_status,
)


def parse_args():
    parser = ArgumentParser(
        description=(
            "Process a D&J Excel export, compare it with the latest local "
            "snapshot, and save the new snapshot."
        )
    )
    parser.add_argument("input", type=Path, help="Path to D&J .xlsx export")
    parser.add_argument(
        "--status-output",
        type=Path,
        default=Path("data/dj/reports/dj_status_report.csv"),
    )
    parser.add_argument(
        "--snapshot-dir",
        type=Path,
        default=Path("data/dj/snapshots"),
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("data/dj/reports"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    rows = read_dj_export(args.input)
    evaluated = evaluate_dj_rows(rows, today=date.today())
    dataframe = save_dj_status_report(evaluated, args.status_output)

    print(f"D&J article rows: {len(dataframe):,}")
    print(f"Unique products: {dataframe['product_id'].nunique():,}")
    for status, count in summarize_dj_statuses(evaluated).items():
        print(f"{status}: {count:,}")

    result = compare_and_snapshot_dj_status(
        args.status_output,
        snapshot_dir=args.snapshot_dir,
        reports_dir=args.reports_dir,
    )

    if result.previous_snapshot is None:
        print("Previous snapshot: none (baseline created)")
    else:
        print(f"Previous snapshot: {result.previous_snapshot}")
        print(f"SKU-level changes: {result.sku_change_count:,}")
        print(f"Product/color changes: {result.entity_change_count:,}")
        print(f"SKU change report: {result.sku_change_report}")
        print(f"Product/color report: {result.entity_change_report}")
        print(f"Shopify dry-run actions: {result.shopify_plan_count:,}")
        print(
            "Auto-apply eligible: "
            f"{result.shopify_auto_apply_eligible_count:,}"
        )
        print(f"Shopify dry-run report: {result.shopify_dry_run_report}")

    print(f"Current snapshot: {result.current_snapshot}")
    print("Shopify writes performed: 0")


if __name__ == "__main__":
    main()
