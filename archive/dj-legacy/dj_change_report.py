from argparse import ArgumentParser
from pathlib import Path

import pandas as pd

from ecommerce_product_importer.services.dj_change_report import (
    compare_dj_status_reports,
    save_dj_change_report,
    summarize_dj_changes,
)


def parse_args():
    parser = ArgumentParser(
        description="Compare two D&J lifecycle status report CSV files."
    )
    parser.add_argument("previous", type=Path, help="Older D&J status CSV")
    parser.add_argument("current", type=Path, help="Newer D&J status CSV")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/dj/reports/dj_change_report.csv"),
        help="Output CSV path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    previous = pd.read_csv(args.previous, dtype={"sku": "string"})
    current = pd.read_csv(args.current, dtype={"sku": "string"})

    changes = compare_dj_status_reports(previous, current)
    save_dj_change_report(changes, args.output)

    print(f"Changes: {len(changes):,}")
    for change_type, count in summarize_dj_changes(changes).items():
        print(f"{change_type}: {count:,}")

    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
