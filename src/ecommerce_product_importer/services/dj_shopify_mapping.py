from pathlib import Path
import re

import pandas as pd

from ecommerce_product_importer.services.dj_lifecycle import (
    EvaluatedDJProductRow,
)


PREVIEW_COLUMNS = [
    "Handle",
    "Title",
    "Body (HTML)",
    "Vendor",
    "Source Category",
    "Collection Mapping Status",
    "Tags",
    "Option1 Name",
    "Option1 Value",
    "Option2 Name",
    "Option2 Value",
    "Variant SKU",
    "Variant Barcode",
    "Main Image",
    "Image URLs",
    "Supplier Dealer Price",
    "Supplier Recommended Price",
    "Shopify Price",
    "Price Status",
]


def _slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def _unique_images(
    main_image: str | None,
    image_urls: tuple[str, ...],
) -> str:
    ordered: list[str] = []

    for image in (main_image, *image_urls):
        if image and image not in ordered:
            ordered.append(image)

    return ";".join(ordered)


def build_dj_shopify_preview(
    rows: list[EvaluatedDJProductRow],
) -> pd.DataFrame:
    """
    Map evaluated D&J rows to a Shopify-oriented review preview.

    Price and collection mapping are intentionally left unresolved.
    No Shopify API calls are made.
    """
    records: list[dict] = []

    for evaluated in rows:
        product = evaluated.product
        lifecycle = evaluated.lifecycle
        handle = f"dj-{_slug(product.product_id)}"

        records.append(
            {
                "Handle": handle,
                "Title": product.product_name,
                "Body (HTML)": product.description,
                "Vendor": product.brand,
                "Source Category": product.category,
                "Collection Mapping Status": "REVIEW_REQUIRED",
                "Tags": ",".join(sorted(lifecycle.shopify_tags)),
                "Option1 Name": "Färg",
                "Option1 Value": product.color,
                "Option2 Name": "Storlek",
                "Option2 Value": product.size_name,
                "Variant SKU": product.sku,
                "Variant Barcode": product.ean or "",
                "Main Image": product.main_image or "",
                "Image URLs": _unique_images(
                    product.main_image,
                    product.image_urls,
                ),
                "Supplier Dealer Price": product.dealer_price,
                "Supplier Recommended Price": product.recommended_price,
                "Shopify Price": None,
                "Price Status": "REVIEW_REQUIRED",
            }
        )

    return pd.DataFrame(records, columns=PREVIEW_COLUMNS)


def save_dj_shopify_preview(
    rows: list[EvaluatedDJProductRow],
    output_path: Path,
) -> pd.DataFrame:
    """Save a local Shopify mapping preview and return the dataframe."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    dataframe = build_dj_shopify_preview(rows)
    dataframe.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )
    return dataframe
