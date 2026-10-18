from pathlib import Path

import pandas as pd

from ecommerce_product_importer.readers.dj_reader import DJProductRow


CATEGORY_COLUMNS = [
    "source_category",
    "unique_products",
    "sku_rows",
    "brands",
    "collection_mapping",
    "mapping_status",
]

PRICE_COLUMNS = [
    "sku",
    "product_id",
    "product_name",
    "brand",
    "dealer_price",
    "recommended_price",
    "recommended_to_dealer_ratio",
    "price_rule",
    "price_status",
]


def build_dj_category_review(rows: list[DJProductRow]) -> pd.DataFrame:
    """Summarize D&J source categories before Shopify collection mapping."""
    if not rows:
        return pd.DataFrame(columns=CATEGORY_COLUMNS)

    frame = pd.DataFrame(
        [
            {
                "product_id": row.product_id,
                "brand": row.brand,
                "category": row.category,
                "sku": row.sku,
            }
            for row in rows
        ]
    )

    records: list[dict] = []
    for category, group in frame.groupby("category", dropna=False):
        category_text = "" if pd.isna(category) else str(category).strip()
        brands = sorted(
            {
                str(value).strip()
                for value in group["brand"].dropna()
                if str(value).strip()
            }
        )

        records.append(
            {
                "source_category": category_text,
                "unique_products": int(group["product_id"].nunique()),
                "sku_rows": int(len(group)),
                "brands": ";".join(brands),
                "collection_mapping": "",
                "mapping_status": "REVIEW_REQUIRED",
            }
        )

    return pd.DataFrame(records, columns=CATEGORY_COLUMNS).sort_values(
        ["unique_products", "source_category"],
        ascending=[False, True],
        ignore_index=True,
    )


def build_dj_price_review(rows: list[DJProductRow]) -> pd.DataFrame:
    """Show D&J price inputs without assuming VAT basis or Shopify price."""
    records: list[dict] = []

    for row in rows:
        ratio = None
        if (
            row.dealer_price is not None
            and row.recommended_price is not None
            and row.dealer_price != 0
        ):
            ratio = round(row.recommended_price / row.dealer_price, 4)

        records.append(
            {
                "sku": row.sku,
                "product_id": row.product_id,
                "product_name": row.product_name,
                "brand": row.brand,
                "dealer_price": row.dealer_price,
                "recommended_price": row.recommended_price,
                "recommended_to_dealer_ratio": ratio,
                "price_rule": "",
                "price_status": "REVIEW_REQUIRED",
            }
        )

    return pd.DataFrame(records, columns=PRICE_COLUMNS)


def save_dj_business_rule_reviews(
    rows: list[DJProductRow],
    reports_dir: Path,
) -> tuple[Path, Path]:
    """Save local category and price review files."""
    reports_dir.mkdir(parents=True, exist_ok=True)

    category_path = reports_dir / "dj_category_review.csv"
    price_path = reports_dir / "dj_price_review.csv"

    build_dj_category_review(rows).to_csv(
        category_path,
        index=False,
        encoding="utf-8-sig",
    )
    build_dj_price_review(rows).to_csv(
        price_path,
        index=False,
        encoding="utf-8-sig",
    )

    return category_path, price_path
