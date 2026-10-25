"""Safely assign existing D&J draft products to manual Shopify collections.

Uses the validated CSV plan and read-only catalog helpers from
dj_shopify_collections_preview.py. Dry-run by default.

Run:
    python scripts/dj_shopify_collections_apply.py
    python scripts/dj_shopify_collections_apply.py --apply --confirm APPLY-DJ-COLLECTIONS
"""

import argparse
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd

from dj_shopify_collections_preview import (
    CATEGORIES,
    PARENT,
    PLAN,
    collection_members,
    fetch_catalog,
    graphql,
)
from ecommerce_product_importer.services.shopify_sync import (
    get_access_token,
    get_shopify_config,
)

CONFIRMATION = "APPLY-DJ-COLLECTIONS"
LOG_DIR = Path("data/dj/reports")
CHUNK_SIZE = 40

ADD_PRODUCTS = """
mutation ($id: ID!, $productIds: [ID!]!) {
  collectionAddProducts(id: $id, productIds: $productIds) {
    userErrors { field message }
  }
}
"""


def load_plan() -> pd.DataFrame:
    plan = pd.read_csv(PLAN, dtype=str).fillna("")
    required = {"Handle", "Target Collection"}
    if not required.issubset(plan.columns):
        raise ValueError(f"Missing plan columns: {required - set(plan.columns)}")
    if len(plan) != 456 or plan["Handle"].nunique() != 456:
        raise ValueError("Expected exactly 456 unique D&J handles")
    if not plan["Handle"].str.startswith("dj-").all():
        raise ValueError("Non-D&J handle in plan")
    unknown = set(plan["Target Collection"]) - CATEGORIES
    if unknown:
        raise ValueError(f"Unknown collections: {sorted(unknown)}")
    return plan


def build_pending(plan, products, collections, memberships):
    pending = defaultdict(list)
    for _, row in plan.iterrows():
        handle = row["Handle"]
        product = products.get(handle)
        if product is None:
            raise ValueError(f"Product missing in Shopify: {handle}")
        if product["status"] != "DRAFT":
            raise ValueError(f"Product not DRAFT: {handle}")
        for name in (PARENT, row["Target Collection"]):
            if product["id"] not in memberships[name]:
                pending[name].append((handle, product["id"]))
    return pending


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--confirm", default="")
    args = parser.parse_args()
    if args.apply and args.confirm != CONFIRMATION:
        parser.error(f"--apply requires --confirm {CONFIRMATION}")

    plan = load_plan()
    shop, client_id, secret = get_shopify_config()
    token = get_access_token(shop, client_id, secret)
    print("Hämtar produkter och produktserier från Shopify...", flush=True)
    products, collections = fetch_catalog(shop, token)

    targets = CATEGORIES | {PARENT}
    missing = targets - collections.keys()
    if missing:
        raise SystemExit(f"Missing Shopify collections: {sorted(missing)}")
    automated = [n for n in targets if collections[n]["ruleSet"] is not None]
    if automated:
        raise SystemExit(f"Not manual collections: {automated}")

    memberships = {
        name: collection_members(shop, token, collections[name]["id"])
        for name in sorted(targets)
    }
    pending = build_pending(plan, products, collections, memberships)
    total = sum(len(items) for items in pending.values())
    print(f"Verified D&J products: {len(plan)} (all DRAFT)")
    print(f"Collection memberships missing: {total}")
    for name in sorted(targets):
        print(f"  {name}: {len(pending[name])} to add")
    print("Mode:", "APPLY" if args.apply else "DRY_RUN")

    if not args.apply:
        print("Shopify writes performed: 0")
        return

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"dj_collection_apply_{datetime.now():%Y%m%d_%H%M%S}.csv"
    completed = 0
    try:
        with log_path.open("w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["collection", "handles", "status", "details"])
            file.flush()
            for name in sorted(targets):
                items = pending[name]
                for i in range(0, len(items), CHUNK_SIZE):
                    chunk = items[i : i + CHUNK_SIZE]
                    handles = ";".join(h for h, _ in chunk)
                    try:
                        response = graphql(
                            shop,
                            token,
                            ADD_PRODUCTS,
                            {
                                "id": collections[name]["id"],
                                "productIds": [p for _, p in chunk],
                            },
                        )
                        errors = (
                            response["collectionAddProducts"].get("userErrors") or []
                        )
                        if errors:
                            raise RuntimeError(str(errors))
                    except Exception as exc:
                        writer.writerow(
                            [name, handles, "FAILED_OR_UNCERTAIN", str(exc)]
                        )
                        file.flush()
                        raise RuntimeError(
                            f"Stopped at {name}. Check membership before retrying."
                        ) from exc
                    writer.writerow([name, handles, "ADDED", ""])
                    file.flush()
                    completed += len(chunk)
                    print(f"{name}: added {len(chunk)}")
    finally:
        print(f"Confirmed assignments this run: {completed}")
        print(f"Log: {log_path}")
    print("Run the read-only preview again to verify all memberships.")


if __name__ == "__main__":
    main()
