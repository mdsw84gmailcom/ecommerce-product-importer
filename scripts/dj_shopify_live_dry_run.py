from argparse import ArgumentParser
from datetime import date
from pathlib import Path

from ecommerce_product_importer.readers.dj_reader import read_dj_export
from ecommerce_product_importer.services.dj_lifecycle import evaluate_dj_rows
from ecommerce_product_importer.services.dj_shopify_live_plan import (
    build_dj_live_dry_run_plan,
    save_dj_live_dry_run_reports,
    summarize_plan,
)
from ecommerce_product_importer.services.dj_shopify_mapping import (
    build_dj_shopify_preview,
)
from ecommerce_product_importer.services.shopify_sync import (
    fetch_products,
    get_access_token,
    get_shopify_config,
)


def parse_args():
    parser = ArgumentParser(
        description=(
            "Compare the current D&J export with live Shopify data. "
            "This command is read-only and performs no Shopify writes."
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
    evaluated = evaluate_dj_rows(rows, today=date.today())
    preview = build_dj_shopify_preview(evaluated)

    shop, client_id, client_secret = get_shopify_config()
    access_token = get_access_token(shop, client_id, client_secret)
    live_products = fetch_products(shop, access_token)

    variant_comparison, product_comparison, plan = build_dj_live_dry_run_plan(
        live_products,
        preview,
    )
    variant_path, product_path = save_dj_live_dry_run_reports(
        variant_comparison,
        product_comparison,
        args.reports_dir,
    )
    counts = summarize_plan(plan)

    print(f"D&J preview rows: {len(preview):,}")
    print(f"D&J products: {preview['Handle'].nunique():,}")
    print(f"Live Shopify products fetched: {len(live_products):,}")
    print("")
    print(f"New variants: {counts['variants_new']:,}")
    print(f"Updated variants: {counts['variants_updated']:,}")
    print(f"Discontinued D&J variants: {counts['variants_discontinued']:,}")
    print(f"New products: {counts['products_new']:,}")
    print(f"Updated products: {counts['products_updated']:,}")
    print(f"Discontinued D&J products: {counts['products_discontinued']:,}")
    print("")
    print(
        "Collection mappings requiring review: "
        f"{(preview['Collection Mapping Status'] == 'REVIEW_REQUIRED').sum():,}"
    )
    print(
        "Prices requiring review: "
        f"{(preview['Price Status'] == 'REVIEW_REQUIRED').sum():,}"
    )
    print("Shopify writes performed: 0")
    print(f"Variant comparison: {variant_path}")
    print(f"Product comparison: {product_path}")


if __name__ == "__main__":
    main()
