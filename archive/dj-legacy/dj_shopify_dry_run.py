from argparse import ArgumentParser
from pathlib import Path

import pandas as pd

from ecommerce_product_importer.services.dj_shopify_plan import (
    build_dj_shopify_dry_run_plan,
    save_dj_shopify_dry_run_plan,
    summarize_dj_shopify_plan,
)


def parse_args():
    parser = ArgumentParser(
        description=(
            "Build a read-only Shopify action plan from a D&J change report."
        )
    )
    parser.add_argument("changes", type=Path, help="D&J change report CSV")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/dj/reports/dj_shopify_dry_run.csv"),
        help="Output CSV path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    changes = pd.read_csv(args.changes, dtype={"sku": "string"})
    plan = build_dj_shopify_dry_run_plan(changes)
    save_dj_shopify_dry_run_plan(plan, args.output)

    print(f"Planned actions: {len(plan):,}")
    for action, count in summarize_dj_shopify_plan(plan).items():
        print(f"{action}: {count:,}")

    auto_count = int(plan["auto_apply_allowed"].sum()) if not plan.empty else 0
    review_count = len(plan) - auto_count
    print(f"Auto-apply eligible: {auto_count:,}")
    print(f"Manual review required: {review_count:,}")
    print("Shopify writes performed: 0")
    print(f"Plan: {args.output}")


if __name__ == "__main__":
    main()
