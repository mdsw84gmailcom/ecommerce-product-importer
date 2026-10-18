from argparse import ArgumentParser
from datetime import date
from pathlib import Path

from ecommerce_product_importer.readers.dj_reader import read_dj_export
from ecommerce_product_importer.services.dj_lifecycle import evaluate_dj_rows
from ecommerce_product_importer.services.dj_shopify_create_plan import (
    build_dj_create_plans,
)
from ecommerce_product_importer.services.dj_shopify_executor import (
    execute_dj_product_create,
)
from ecommerce_product_importer.services.dj_shopify_live_plan import (
    build_dj_live_dry_run_plan,
)
from ecommerce_product_importer.services.dj_shopify_mapping import (
    build_dj_shopify_preview,
)
from ecommerce_product_importer.services.dj_shopify_mutation_plan import (
    build_dj_mutation_plan,
)
from ecommerce_product_importer.services.shopify_sync import (
    fetch_products,
    get_access_token,
    get_shopify_config,
)


def parse_args():
    parser = ArgumentParser(
        description=(
            "Create at most one D&J product in Shopify. "
            "Dry-run is the default; --apply is required for a write."
        )
    )
    parser.add_argument("input", type=Path, help="Path to D&J .xlsx export")
    parser.add_argument(
        "--handle",
        required=True,
        help="Exact D&J Shopify handle, for example dj-410001",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually create the selected product as DRAFT",
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

    if args.handle not in new_handles:
        raise SystemExit(
            f"{args.handle} is not classified as a NEW D&J product. "
            "No write attempted."
        )

    create_plans = [
        plan
        for plan in build_dj_create_plans(preview, {args.handle})
        if plan.handle == args.handle
    ]
    if len(create_plans) != 1:
        raise SystemExit(
            f"Expected exactly one create plan for {args.handle}; "
            f"found {len(create_plans)}. No write attempted."
        )

    operations = build_dj_mutation_plan(create_plans)

    result = execute_dj_product_create(
        shop=shop,
        access_token=access_token,
        operations=operations,
        handle=args.handle,
        apply=args.apply,
    )

    print(f"Handle: {result.handle}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY_RUN'}")
    print(f"Status: {result.status}")
    print(f"Mutations planned: {len(operations)}")
    print("Product status required: DRAFT")
    print("Delete mutations allowed: no")
    print("Publish mutations allowed: no")
    print(f"Shopify writes performed: {len(result.completed_mutations)}")

    if result.product_id:
        print(f"Created product ID: {result.product_id}")
    if result.initial_variant_id:
        print(f"Initial variant ID: {result.initial_variant_id}")


if __name__ == "__main__":
    main()
