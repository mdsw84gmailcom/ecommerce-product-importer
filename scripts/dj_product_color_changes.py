from argparse import ArgumentParser
from pathlib import Path

import pandas as pd

from ecommerce_product_importer.services.dj_entity_changes import (
    compare_dj_product_color_changes,
    save_dj_product_color_changes,
    summarize_dj_product_color_changes,
)


def parse_args():
    parser = ArgumentParser(
        description=(
            "Compare two D&J status snapshots at product and color level."
        )
    )
    parser.add_argument("previous", type=Path)
    parser.add_argument("current", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/dj/reports/dj_product_color_changes.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    previous = pd.read_csv(args.previous, dtype=str)
    current = pd.read_csv(args.current, dtype=str)

    changes = compare_dj_product_color_changes(previous, current)
    save_dj_product_color_changes(changes, args.output)

    print(f"Entity changes: {len(changes):,}")
    for change_type, count in summarize_dj_product_color_changes(changes).items():
        print(f"{change_type}: {count:,}")
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
