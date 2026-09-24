import os
import pandas as pd

import requests
from dotenv import load_dotenv

SHOPIFY_API_VERSION = "2026-07"


def get_shopify_config() -> tuple[str, str]:
    """Load Shopify configuration without making an API request."""
    load_dotenv()

    shop = os.getenv("SHOPIFY_SHOP")
    client_id = os.getenv("SHOPIFY_CLIENT_ID")
    client_secret = os.getenv("SHOPIFY_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError("Missing Shopify client credentials in .env")

    shop = shop.removeprefix("https://").removeprefix("http://")
    shop = shop.rstrip("/")

    if not shop.endswith(".myshopify.com"):
        shop = f"{shop}.myshopify.com"

    return shop, client_id, client_secret


def get_graphql_url(shop: str) -> str:
    """Build the Shopify Admin GraphQL endpoint."""
    return f"https://{shop}/admin/api/" f"{SHOPIFY_API_VERSION}/graphql.json"


def get_access_token(
    shop: str,
    client_id: str,
    client_secret: str,
) -> str:
    """Request a temporary Shopify Admin API access token."""
    token_url = f"https://{shop}/admin/oauth/access_token"

    response = requests.post(
        token_url,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    access_token = data.get("access_token")

    if not access_token:
        raise RuntimeError("Shopify did not return an access token")

    return access_token


def fetch_products(shop: str, access_token: str) -> list[dict]:
    """Fetch all Shopify products and all variants without modifying store data."""
    product_query = """
    query Products($cursor: String) {
      products(first: 100, after: $cursor) {
        nodes {
          id
          title
          handle
          variants(first: 100) {
            nodes {
              id
              sku
              barcode
              price
            }
            pageInfo {
              hasNextPage
              endCursor
            }
          }
        }
        pageInfo {
          hasNextPage
          endCursor
        }
      }
    }
    """

    variant_query = """
    query ProductVariants($productId: ID!, $cursor: String) {
      product(id: $productId) {
        variants(first: 100, after: $cursor) {
          nodes {
            id
            sku
            barcode
            price
          }
          pageInfo {
            hasNextPage
            endCursor
          }
        }
      }
    }
    """

    headers = {
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    }

    products = []
    product_cursor = None

    while True:
        response = requests.post(
            get_graphql_url(shop),
            headers=headers,
            json={
                "query": product_query,
                "variables": {"cursor": product_cursor},
            },
            timeout=30,
        )

        response.raise_for_status()
        data = response.json()

        if "errors" in data:
            raise RuntimeError(data["errors"])

        result = data["data"]["products"]

        for product in result["nodes"]:
            variants = product["variants"]
            all_variants = list(variants["nodes"])

            variant_cursor = variants["pageInfo"]["endCursor"]

            while variants["pageInfo"]["hasNextPage"]:
                variant_response = requests.post(
                    get_graphql_url(shop),
                    headers=headers,
                    json={
                        "query": variant_query,
                        "variables": {
                            "productId": product["id"],
                            "cursor": variant_cursor,
                        },
                    },
                    timeout=30,
                )

                variant_response.raise_for_status()
                variant_data = variant_response.json()

                if "errors" in variant_data:
                    raise RuntimeError(variant_data["errors"])

                variants = variant_data["data"]["product"]["variants"]

                all_variants.extend(variants["nodes"])
                variant_cursor = variants["pageInfo"]["endCursor"]

            product["variants"]["nodes"] = all_variants
            products.append(product)

        if not result["pageInfo"]["hasNextPage"]:
            break

        product_cursor = result["pageInfo"]["endCursor"]

    return products


def build_shopify_variant_dataframe(products: list[dict]) -> pd.DataFrame:
    """Convert Shopify product data into one row per variant."""
    rows = []

    for product in products:
        for variant in product["variants"]["nodes"]:
            rows.append(
                {
                    "shopify_product_id": product["id"],
                    "shopify_variant_id": variant["id"],
                    "handle": product["handle"],
                    "title": product["title"],
                    "variant_sku": variant["sku"],
                    "price": variant["price"],
                    "barcode": variant["barcode"],
                }
            )

    return pd.DataFrame(rows)


def normalize_value(value) -> str:
    """Normalize values before comparing Shopify and supplier data."""
    if pd.isna(value):
        return ""

    return str(value).strip()


def compare_variants(
    live: pd.DataFrame,
    new: pd.DataFrame,
) -> pd.DataFrame:
    """Classify variants as NEW, UPDATED, UNCHANGED or DISCONTINUED."""

    live = live.rename(
        columns={
            "variant_sku": "sku",
            "price": "live_price",
            "barcode": "live_barcode",
        }
    )

    new = new.rename(
        columns={
            "Variant SKU": "sku",
            "Variant Price": "new_price",
            "Variant Barcode": "new_barcode",
        }
    )

    comparison = live.merge(
        new[["sku", "new_price", "new_barcode"]],
        how="outer",
        on="sku",
        indicator=True,
    )

    def classify(row):
        if row["_merge"] == "right_only":
            return "NEW"

        if row["_merge"] == "left_only":
            return "DISCONTINUED"

        price_changed = float(row["live_price"]) != float(row["new_price"])

        barcode_changed = normalize_value(row["live_barcode"]) != normalize_value(
            row["new_barcode"]
        )

        if price_changed or barcode_changed:
            return "UPDATED"

        return "UNCHANGED"

    comparison["status"] = comparison.apply(classify, axis=1)

    return comparison
