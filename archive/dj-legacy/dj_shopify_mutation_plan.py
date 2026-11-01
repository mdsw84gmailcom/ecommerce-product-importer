from argparse import ArgumentParser
from datetime import date
from pathlib import Path

from ecommerce_product_importer.readers.dj_reader import read_dj_export
from ecommerce_product_importer.services.dj_lifecycle import evaluate_dj_rows
from ecommerce_product_importer.services.dj_shopify_create_plan import (
    build_dj_create_plans,
)
from ecommerce_product_importer.services.dj_shopify_live_plan import (
    build_dj_live_dry_run_plan,
)
from ecommerce_product_importer.services.dj_shopify_mapping import (
    build_dj_shopify_preview,
)
from ecommerce_product_importer.services.dj_shopify_mutation_plan import (
    build_dj_mutation_plan,
    save_dj_mutation_plan,
    summarize_mutation_plan,
)
from ecommerce_product_importer.services.shopify_sync import (
    fetch_products,
    get_access_token,
    get_shopify_config,
)


def parse_args():
    parser = ArgumentParser(
        description=(
            "Build the exact Shopify mutation sequence for new D&J products. "
            "This command is dry-run only and performs no Shopify writes."
        )
    )
    parser.add_argument("input", type=Path, help="Path to D&J .xlsx export")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/dj/reports/dj_shopify_mutation_plan.jsonl"),
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

    _, product_comparison, _ = build_dj_live_dry_run_plan(
        live_products,
        preview,
    )
    new_handles = set(
        product_comparison.loc[
            product_comparison["status"] == "NEW",
            "handle",
        ].astype(str)
    )

    create_plans = build_dj_create_plans(preview, new_handles)
    operations = build_dj_mutation_plan(create_plans)
    save_dj_mutation_plan(operations, args.output)
    summary = summarize_mutation_plan(operations)

    additional_variant_count = sum(
        len(plan.additional_variants)
        for plan in create_plans
    )
    products_with_images = sum(bool(plan.image_urls) for plan in create_plans)
    image_count = sum(len(plan.image_urls) for plan in create_plans)

    print(f"New D&J products: {len(create_plans):,}")
    print(f"Total D&J variants: {len(preview):,}")
    print(f"productCreate mutations planned: {summary['productCreate']:,}")
    print(
        "Initial variant update mutations planned: "
        f"{summary['productVariantsBulkUpdate']:,}"
    )
    print(
        "Additional variant create mutations planned: "
        f"{summary['productVariantsBulkCreate']:,}"
    )
    print(f"Additional variants inside bulk creates: {additional_variant_count:,}")
    print(f"Products with images planned: {products_with_images:,}")
    print(f"Product images planned: {image_count:,}")
    print("All products remain DRAFT: yes")
    print("Delete mutations planned: 0")
    print("Publish mutations planned: 0")
    print("Shopify writes performed: 0")
    print(f"Mutation plan: {args.output}")


if __name__ == "__main__":
    main()
