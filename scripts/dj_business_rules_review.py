from argparse import ArgumentParser
from pathlib import Path

from ecommerce_product_importer.readers.dj_reader import read_dj_export
from ecommerce_product_importer.services.dj_business_rules import (
    build_dj_category_review,
    build_dj_price_review,
    save_dj_business_rule_reviews,
)


def parse_args():
    parser = ArgumentParser(
        description=(
            "Review D&J categories and price inputs before defining "
            "Shopify business rules."
        )
    )
    parser.add_argument("input", type=Path, help="Path to D&J .xlsx export")
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=Path("data/dj/reports"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = read_dj_export(args.input)

    categories = build_dj_category_review(rows)
    prices = build_dj_price_review(rows)
    category_path, price_path = save_dj_business_rule_reviews(
        rows,
        args.reports_dir,
    )

    print(f"Source categories: {len(categories):,}")
    print(f"Price rows: {len(prices):,}")
    print(
        "Rows missing dealer price: "
        f"{prices['dealer_price'].isna().sum():,}"
    )
    print(
        "Rows missing recommended price: "
        f"{prices['recommended_price'].isna().sum():,}"
    )

    print("\nTop source categories:")
    for _, row in categories.head(15).iterrows():
        print(
            f"- {row['source_category']}: "
            f"{row['unique_products']} products / {row['sku_rows']} SKUs"
        )

    ratios = prices["recommended_to_dealer_ratio"].dropna()
    if not ratios.empty:
        print(
            "\nRecommended/dealer ratio: "
            f"min={ratios.min():.2f}, "
            f"median={ratios.median():.2f}, "
            f"max={ratios.max():.2f}"
        )

    print("\nNo VAT basis assumed.")
    print("No Shopify selling price calculated.")
    print("Shopify writes performed: 0")
    print(f"Category review: {category_path}")
    print(f"Price review: {price_path}")


if __name__ == "__main__":
    main()
