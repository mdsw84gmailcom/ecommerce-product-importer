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
    "Suggested Collection",
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
    "Proposed Shopify Price",
    "Shopify Price",
    "Price Status",
]



CATEGORY_COLLECTION_MAP = {
    "Badrum;Badrock": "Badrockar",
    "Badrum;Frotté": "Handdukar & frotté",
    "Flaskor;Vattenflaska": "Vattenflaskor",
    "Inredning;Pläd": "Plädar",
    "Kök;Kniv": "Knivar",
    "Kök;Kökshandduk": "Kökshanddukar",
    "Kök;Köksredskap": "Köksredskap",
    "Kök;Servering": "Servering",
    "Kök;Skärbräda": "Skärbrädor",
    "Sovrum;Bäddset": "Bäddset",
    "Sovrum;Kudde": "Kuddar",
    "Sovrum;Kuddfodral": "Kuddfodral",
    "Sovrum;Täcke": "Täcken",
    "Sovrum;Underlakan": "Lakan",
}


def _suggest_collection(source_category: str) -> tuple[str, str]:
    category = source_category.strip()
    if not category:
        return "", "REVIEW_REQUIRED"

    collection = CATEGORY_COLLECTION_MAP.get(category)
    if collection is None:
        return "", "REVIEW_REQUIRED"

    return collection, "SUGGESTED"


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

    Recommended retail price is shown as a proposed Shopify price, but
    remains blocked until the VAT basis has been verified. Known source
    categories receive suggested collections; unknown categories stay
    REVIEW_REQUIRED. No Shopify API calls are made.
    """
    records: list[dict] = []

    for evaluated in rows:
        product = evaluated.product
        lifecycle = evaluated.lifecycle
        handle = f"dj-{_slug(product.product_id)}"
        suggested_collection, collection_status = _suggest_collection(
            product.category
        )

        records.append(
            {
                "Handle": handle,
                "Title": product.product_name,
                "Body (HTML)": product.description,
                "Vendor": product.brand,
                "Source Category": product.category,
                "Suggested Collection": suggested_collection,
                "Collection Mapping Status": collection_status,
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
                "Proposed Shopify Price": product.recommended_price,
                "Shopify Price": None,
                "Price Status": "VAT_VERIFICATION_REQUIRED",
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
