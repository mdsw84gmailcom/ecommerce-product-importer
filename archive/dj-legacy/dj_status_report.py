from argparse import ArgumentParser
from datetime import date
from pathlib import Path

from ecommerce_product_importer.readers.dj_reader import read_dj_export
from ecommerce_product_importer.services.dj_lifecycle import evaluate_dj_rows
from ecommerce_product_importer.services.dj_report import (
    save_dj_status_report,
    summarize_dj_statuses,
)


def parse_args():
    parser = ArgumentParser(
        description="Create a lifecycle status report from a D&J Excel export."
    )
    parser.add_argument("input", type=Path, help="Path to D&J .xlsx export")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/reports/dj_status_report.csv"),
        help="CSV output path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    rows = read_dj_export(args.input)
    evaluated = evaluate_dj_rows(rows, today=date.today())
    dataframe = save_dj_status_report(evaluated, args.output)
    summary = summarize_dj_statuses(evaluated)

    print(f"D&J article rows: {len(dataframe):,}")
    print(f"Unique products: {dataframe['product_id'].nunique():,}")

    for status, count in summary.items():
        print(f"{status}: {count:,}")

    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
