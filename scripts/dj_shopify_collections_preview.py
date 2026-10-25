"""Read-only plan for assigning existing D&J Shopify products to collections.

Run from the repository root:
    python scripts/dj_shopify_collections_preview.py
Does not perform Shopify mutations.
"""

import csv
import time
from collections import Counter
from pathlib import Path

import pandas as pd
import requests
from requests.exceptions import ConnectionError, Timeout, SSLError

from ecommerce_product_importer.services.shopify_sync import (
    get_access_token,
    get_graphql_url,
    get_shopify_config,
)

PLAN = Path("data/dj/reports/dj_collections_plan.csv")
REPORT = Path("data/dj/reports/dj_collections_assignments.csv")
PARENT = "Presenter & Gåvor"
CATEGORIES = {
    "Kök & Matlagning",
    "Sovrum & Textilier",
    "Friluftsliv & Fritid",
    "Hem & Inredning",
    "Väskor & Accessoarer",
    "Bad & Spa",
    "Glas & Servering",
    "Presentset & Gåvoset",
    "Spel & Lek",
}


def graphql(shop: str, token: str, query: str, variables: dict) -> dict:
    # Queries are safe to retry. NEVER retry a mutation automatically:
    # a lost response could mean that Shopify already performed the write.
    read_only = query.lstrip().startswith("query")
    attempts = 4 if read_only else 1
    for attempt in range(1, attempts + 1):
        try:
            response = requests.post(
                get_graphql_url(shop),
                headers={
                    "X-Shopify-Access-Token": token,
                    "Content-Type": "application/json",
                },
                json={"query": query, "variables": variables},
                timeout=(10, 30),
            )
            if read_only and response.status_code in (429, 500, 502, 503, 504):
                response.raise_for_status()
            response.raise_for_status()
            data = response.json()
            if data.get("errors"):
                errors = data["errors"]
                throttled = all(
                    e.get("extensions", {}).get("code") == "THROTTLED" for e in errors
                )
                if read_only and throttled and attempt < attempts:
                    raise RuntimeError("Shopify query throttled")
                raise RuntimeError(f"Shopify GraphQL errors: {errors}")
            return data["data"]
        except (
            ConnectionError,
            Timeout,
            SSLError,
            RuntimeError,
            requests.HTTPError,
        ) as exc:
            if attempt == attempts or not read_only:
                raise
            delay = min(2 ** (attempt - 1), 8)
            print(
                f"  Tillfälligt Shopify-fel ({type(exc).__name__}). "
                f"Försök {attempt + 1}/{attempts} om {delay} s...",
                flush=True,
            )
            time.sleep(delay)
    raise AssertionError("Unreachable")


def fetch_catalog(shop: str, token: str) -> tuple[dict, dict]:
    product_query = """
    query ($cursor: String) {
      products(first: 100, after: $cursor) {
        nodes { id handle status }
        pageInfo { hasNextPage endCursor }
      }
    }
    """
    collection_query = """
    query ($cursor: String) {
      collections(first: 100, after: $cursor) {
        nodes { id title ruleSet { rules { column } } }
        pageInfo { hasNextPage endCursor }
      }
    }
    """

    def pages(query: str, key: str) -> list[dict]:
        nodes = []
        cursor = None
        while True:
            result = graphql(shop, token, query, {"cursor": cursor})[key]
            nodes.extend(result["nodes"])
            print(f"  {key}: {len(nodes)} hämtade", flush=True)
            if not result["pageInfo"]["hasNextPage"]:
                return nodes
            cursor = result["pageInfo"]["endCursor"]

    products = {p["handle"]: p for p in pages(product_query, "products")}
    collections = {c["title"]: c for c in pages(collection_query, "collections")}
    return products, collections


def collection_members(shop: str, token: str, collection_id: str) -> set[str]:
    query = """
    query ($id: ID!, $cursor: String) {
      collection(id: $id) {
        products(first: 250, after: $cursor) {
          nodes { id }
          pageInfo { hasNextPage endCursor }
        }
      }
    }
    """
    members = set()
    cursor = None
    while True:
        data = graphql(shop, token, query, {"id": collection_id, "cursor": cursor})
        collection = data["collection"]
        if collection is None:
            raise RuntimeError(f"Missing collection: {collection_id}")
        conn = collection["products"]
        members.update(p["id"] for p in conn["nodes"])
        print(
            f"  Produktserie {collection_id.rsplit('/', 1)[-1]}: "
            f"{len(members)} befintliga produkter",
            flush=True,
        )
        if not conn["pageInfo"]["hasNextPage"]:
            return members
        cursor = conn["pageInfo"]["endCursor"]


def main() -> None:
    df = pd.read_csv(PLAN, dtype=str).fillna("")
    required = {"Handle", "Target Collection"}
    if not required.issubset(df.columns):
        raise SystemExit(f"Missing CSV columns: {required - set(df.columns)}")
    if df["Handle"].duplicated().any():
        raise SystemExit("Duplicate handles in plan: stop and review.")
    if len(df) != 456 or df["Handle"].nunique() != 456:
        raise SystemExit(f"Expected 456 unique D&J products; found {len(df)}.")
    if not df["Handle"].str.startswith("dj-").all():
        raise SystemExit("Non-D&J handle in plan; stopped.")
    unexpected = set(df["Target Collection"]) - CATEGORIES
    if unexpected:
        raise SystemExit(f"Unknown target collections: {sorted(unexpected)}")

    shop, client_id, client_secret = get_shopify_config()
    token = get_access_token(shop, client_id, client_secret)
    products, collections = fetch_catalog(shop, token)

    names = CATEGORIES | {PARENT}
    missing_collections = names - collections.keys()
    if missing_collections:
        raise SystemExit(
            f"Collections missing from Shopify: {sorted(missing_collections)}"
        )
    automated = [name for name in names if collections[name]["ruleSet"] is not None]
    if automated:
        raise SystemExit(f"Collections are automated, not manual: {automated}")

    missing_products = set(df["Handle"]) - products.keys()
    if missing_products:
        raise SystemExit(
            f"Products missing in Shopify: {sorted(missing_products)[:15]}"
        )

    not_draft = [h for h in df["Handle"] if products[h]["status"] != "DRAFT"]
    if not_draft:
        raise SystemExit(
            f"Expected all D&J products to be DRAFT. Non-drafts: {not_draft[:15]}"
        )

    members = {
        name: collection_members(shop, token, collections[name]["id"])
        for name in sorted(names)
    }

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter()
    with REPORT.open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.writer(output)
        writer.writerow(
            ["handle", "product_id", "collection", "collection_id", "action"]
        )
        for _, row in df.iterrows():
            handle = row["Handle"]
            pid = products[handle]["id"]
            for name in (PARENT, row["Target Collection"]):
                action = "ALREADY_IN_COLLECTION" if pid in members[name] else "ADD"
                writer.writerow([handle, pid, name, collections[name]["id"], action])
                counts[action] += 1

    print("D&J products validated:", len(df))
    print("All products DRAFT: yes")
    print("Manual target collections:", len(names))
    print("Already assigned:", counts["ALREADY_IN_COLLECTION"])
    print("Assignments to add:", counts["ADD"])
    print("Report:", REPORT)
    print("Shopify writes performed: 0")


if __name__ == "__main__":
    main()
