import csv
from datetime import datetime
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

MAX_APPLY_BATCH = 500
APPLY_CONFIRMATION = "APPLY-DJ-DRAFTS"


def parse_args():
    parser = ArgumentParser(
        description=(
            "Plan or create a small batch of NEW D&J products in Shopify. "
            "Dry-run is the default."
        )
    )
    parser.add_argument("input", type=Path, help="Path to D&J .xlsx export")
    parser.add_argument(
        "--limit",
        type=int,
        default=5,
        help="Number of NEW products to select, default 5",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually create the selected products as DRAFT",
    )
    parser.add_argument(
        "--confirm",
        default="",
        help=f"Required with --apply: {APPLY_CONFIRMATION}",
    )
    return parser.parse_args()


def validate_apply_args(*, limit: int, apply: bool, confirm: str) -> None:
    if limit < 1:
        raise ValueError("--limit must be at least 1")

    if apply and limit > MAX_APPLY_BATCH:
        raise ValueError(f"Apply batch is limited to {MAX_APPLY_BATCH} products")

    if apply and confirm != APPLY_CONFIRMATION:
        raise ValueError(f"--apply requires --confirm {APPLY_CONFIRMATION}")


def main() -> None:
    args = parse_args()

    try:
        validate_apply_args(
            limit=args.limit,
            apply=args.apply,
            confirm=args.confirm,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

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

    new_handles = sorted(
        set(
            product_comparison.loc[
                product_comparison["status"] == "NEW",
                "handle",
            ].astype(str)
        )
    )

    selected_handles = new_handles[: args.limit]
    create_plans = build_dj_create_plans(
        preview,
        set(selected_handles),
    )
    plans_by_handle = {plan.handle: plan for plan in create_plans}

    print(f"NEW D&J products available: {len(new_handles):,}")
    print(f"Selected products: {len(selected_handles):,}")
    print(f"Mode: {'APPLY' if args.apply else 'DRY_RUN'}")
    print("All products required to remain DRAFT: yes")
    print("Delete mutations allowed: no")
    print("Publish mutations allowed: no")

    completed = 0
    failed = 0

    log_dir = Path("data/dj/reports")
    log_dir.mkdir(parents=True, exist_ok=True)

    log_path = log_dir / (f"dj_import_{datetime.now():%Y%m%d_%H%M%S}.csv")

    with log_path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["handle", "status", "product_id", "error"])

        for handle in selected_handles:
            plan = plans_by_handle.get(handle)

            if plan is None:
                writer.writerow([handle, "FAILED", "", "Missing create plan"])
                failed += 1
                break

            operations = build_dj_mutation_plan([plan])

            try:
                result = execute_dj_product_create(
                    shop=shop,
                    access_token=access_token,
                    operations=operations,
                    handle=handle,
                    apply=args.apply,
                )

                writer.writerow(
                    [
                        handle,
                        result.status,
                        result.product_id or "",
                        "",
                    ]
                )

                if result.status == "CREATED_DRAFT":
                    completed += 1

                print(f"{handle}: {result.status}")

            except Exception as exc:
                failed += 1
                writer.writerow([handle, "FAILED_OR_PARTIAL", "", str(exc)])
                print(f"{handle}: FAILED_OR_PARTIAL - {exc}")
                file.flush()
                break

            file.flush()

    print(f"Products written: {completed}")
    print(f"Failed products: {failed}")
    print(f"Import log: {log_path}")
    print("Shopify writes performed: " + ("yes" if completed else "0"))

    if failed:
        raise SystemExit(
            "Import stopped. Inspect Shopify and the log " "before restarting."
        )


if __name__ == "__main__":
    main()
