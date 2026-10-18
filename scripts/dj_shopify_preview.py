from argparse import ArgumentParser
from datetime import date
from pathlib import Path

from ecommerce_product_importer.readers.dj_reader import read_dj_export
from ecommerce_product_importer.services.dj_lifecycle import evaluate_dj_rows
from ecommerce_product_importer.services.dj_shopify_mapping import (
    save_dj_shopify_preview,
)


def parse_args():
    parser = ArgumentParser(
        description=(
            "Create a read-only Shopify mapping preview from a D&J export."
        )
    )
    parser.add_argument("input", type=Path, help="Path to D&J .xlsx export")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/dj/reports/dj_shopify_preview.csv"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    rows = read_dj_export(args.input)
    evaluated = evaluate_dj_rows(rows, today=date.today())
    preview = save_dj_shopify_preview(evaluated, args.output)

    print(f"Preview rows: {len(preview):,}")
    print(f"Unique products: {preview['Handle'].nunique():,}")
    print(
        "Prices awaiting VAT verification: "
        f"{(preview['Price Status'] == 'VAT_VERIFICATION_REQUIRED').sum():,}"
    )
    print(
        "Suggested collection mappings: "
        f"{(preview['Collection Mapping Status'] == 'SUGGESTED').sum():,}"
    )
    print(
        "Collection mappings requiring review: "
        f"{(preview['Collection Mapping Status'] == 'REVIEW_REQUIRED').sum():,}"
    )
    print("Shopify writes performed: 0")
    print(f"Preview: {args.output}")


if __name__ == "__main__":
    main()
