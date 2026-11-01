from argparse import ArgumentParser
from datetime import date
from pathlib import Path

from ecommerce_product_importer.readers.dj_reader import read_dj_export
from ecommerce_product_importer.services.dj_lifecycle import evaluate_dj_rows
from ecommerce_product_importer.services.dj_shopify_create_plan import (
    build_dj_create_plans,
    save_dj_create_plans,
)
from ecommerce_product_importer.services.dj_shopify_live_plan import (
    build_dj_live_dry_run_plan,
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
            "Build a read-only Shopify create plan for new D&J products. "
            "No Shopify mutations are sent."
        )
    )
    parser.add_argument("input", type=Path, help="Path to D&J .xlsx export")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/dj/reports/dj_shopify_create_plan.jsonl"),
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

    plans = build_dj_create_plans(preview, new_handles)
    save_dj_create_plans(plans, args.output)

    planned_variants = sum(
        1 + len(plan.additional_variants)
        for plan in plans
    )
    review_collections = sum(
        plan.collection_mapping_status == "REVIEW_REQUIRED"
        for plan in plans
    )
    max_variants = max(
        (1 + len(plan.additional_variants) for plan in plans),
        default=0,
    )

    print(f"New D&J products planned: {len(plans):,}")
    print(f"Variants planned: {planned_variants:,}")
    print(f"Products created as DRAFT: {len(plans):,}")
    print(f"Products with collection review: {review_collections:,}")
    print(f"Maximum variants on one product: {max_variants:,}")
    print("Delete operations planned: 0")
    print("Products published automatically: 0")
    print("Shopify writes performed: 0")
    print(f"Create plan: {args.output}")


if __name__ == "__main__":
    main()
