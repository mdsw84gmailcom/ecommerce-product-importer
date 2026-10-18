from collections import Counter
from pathlib import Path

import pandas as pd

from ecommerce_product_importer.services.dj_lifecycle import (
    EvaluatedDJProductRow,
)


def build_dj_status_dataframe(
    rows: list[EvaluatedDJProductRow],
) -> pd.DataFrame:
    """Build a review-friendly status report from evaluated D&J rows."""
    records: list[dict] = []

    for evaluated in rows:
        product = evaluated.product
        lifecycle = evaluated.lifecycle

        records.append(
            {
                "supplier": product.supplier,
                "product_id": product.product_id,
                "sku": product.sku,
                "product_name": product.product_name,
                "brand": product.brand,
                "category": product.category,
                "color": product.color,
                "color_code": product.color_code,
                "size": product.size_name,
                "ean": product.ean,
                "dealer_price": product.dealer_price,
                "recommended_price": product.recommended_price,
                "supplier_tags": ";".join(product.tags),
                "available_from": product.available_from,
                "statuses": ";".join(
                    sorted(status.value for status in lifecycle.statuses)
                ),
                "shopify_tags": ";".join(sorted(lifecycle.shopify_tags)),
            }
        )

    return pd.DataFrame(records)


def summarize_dj_statuses(
    rows: list[EvaluatedDJProductRow],
) -> dict[str, int]:
    """Count lifecycle states across all evaluated D&J article rows."""
    counts: Counter[str] = Counter()

    for evaluated in rows:
        for status in evaluated.lifecycle.statuses:
            counts[status.value] += 1

    return dict(sorted(counts.items()))


def save_dj_status_report(
    rows: list[EvaluatedDJProductRow],
    output_path: Path,
) -> pd.DataFrame:
    """Save the D&J lifecycle report as CSV and return the dataframe."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    dataframe = build_dj_status_dataframe(rows)
    dataframe.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )

    return dataframe
