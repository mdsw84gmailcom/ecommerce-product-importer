from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

import pandas as pd


@dataclass(frozen=True)
class DJCreatePlan:
    """Read-only Shopify create plan for one new D&J product."""

    handle: str
    product_create: dict
    initial_variant: dict
    additional_variants: list[dict]
    suggested_collection: str
    collection_mapping_status: str
    image_urls: list[str]


def _unique(values) -> list[str]:
    result: list[str] = []
    for value in values:
        text = "" if pd.isna(value) else str(value).strip()
        if text and text not in result:
            result.append(text)
    return result


def _variant_payload(
    row: pd.Series,
    *,
    has_color: bool,
    has_size: bool,
) -> dict:
    sku = str(row["Variant SKU"]).strip()

    option_values: list[dict] = []
    if has_color:
        option_values.append(
            {"optionName": "Färg", "name": str(row["Option1 Value"]).strip()}
        )
    if has_size:
        option_values.append(
            {"optionName": "Storlek", "name": str(row["Option2 Value"]).strip()}
        )

    payload = {
        "price": f"{float(row['Shopify Price']):.2f}",
        "inventoryItem": {
            "sku": sku,
            "tracked": False,
        },
        "taxable": True,
        "optionValues": option_values,
    }

    barcode = row.get("Variant Barcode", "")
    if not pd.isna(barcode) and str(barcode).strip():
        payload["barcode"] = str(barcode).strip()

    return payload


def _validate_product_group(handle: str, group: pd.DataFrame) -> list[str]:
    errors: list[str] = []

    required_nonblank = [
        "Handle",
        "Title",
        "Variant SKU",
    ]
    for column in required_nonblank:
        if column not in group.columns:
            errors.append(f"missing column {column}")
            continue

        values = group[column].fillna("").astype(str).str.strip()
        if (values == "").any():
            errors.append(f"blank {column}")

    for column in ("Option1 Value", "Option2 Value"):
        if column not in group.columns:
            errors.append(f"missing column {column}")
            continue

        values = group[column].fillna("").astype(str).str.strip()
        has_values = values != ""
        if has_values.any() and not has_values.all():
            errors.append(f"partially blank {column}")

    if "Shopify Price" not in group.columns:
        errors.append("missing column Shopify Price")
    elif group["Shopify Price"].isna().any():
        errors.append("missing Shopify Price")

    if "Price Status" in group.columns:
        if not (group["Price Status"] == "READY").all():
            errors.append("price not READY")

    if "Variant SKU" in group.columns:
        skus = group["Variant SKU"].fillna("").astype(str).str.strip()
        if skus.duplicated().any():
            errors.append("duplicate SKU inside product")

    for column in ("Title", "Body (HTML)", "Vendor"):
        if column in group.columns:
            values = group[column].fillna("").astype(str).drop_duplicates()
            if len(values) > 1:
                errors.append(f"inconsistent {column}")

    if errors:
        return [f"{handle}: {error}" for error in errors]
    return []


def validate_dj_create_preview(preview: pd.DataFrame) -> list[str]:
    """Return blocking validation errors before any Shopify creation."""
    errors: list[str] = []

    if "Variant SKU" in preview.columns:
        skus = preview["Variant SKU"].fillna("").astype(str).str.strip()
        duplicates = sorted(set(skus[skus.duplicated(keep=False) & (skus != "")]))
        if duplicates:
            errors.append(
                "duplicate SKUs across preview: " + ", ".join(duplicates[:10])
            )

    if "Handle" not in preview.columns:
        return errors + ["preview: missing column Handle"]

    for handle, group in preview.groupby("Handle", sort=True):
        errors.extend(_validate_product_group(str(handle), group))

    return errors


def build_dj_create_plans(
    preview: pd.DataFrame,
    new_handles: set[str],
) -> list[DJCreatePlan]:
    """
    Build Shopify product/variant create payloads without sending mutations.

    Product creation is DRAFT. Shopify productCreate creates one initial
    variant, so the first D&J variant is planned for a subsequent bulk update
    and the remaining variants are planned for productVariantsBulkCreate.
    """
    errors = validate_dj_create_preview(preview)
    if errors:
        raise ValueError("D&J create plan validation failed:\n" + "\n".join(errors))

    plans: list[DJCreatePlan] = []

    selected = preview[preview["Handle"].isin(new_handles)].copy()

    for handle, group in selected.groupby("Handle", sort=True):
        group = group.reset_index(drop=True)
        first = group.iloc[0]

        colors = _unique(group["Option1 Value"])
        sizes = _unique(group["Option2 Value"])
        has_color = bool(colors)
        has_size = bool(sizes)

        tags: list[str] = []
        for tag_cell in group["Tags"].fillna(""):
            for tag in str(tag_cell).split(","):
                tag = tag.strip()
                if tag and tag not in tags:
                    tags.append(tag)

        product_create = {
            "title": str(first["Title"]),
            "handle": str(handle),
            "descriptionHtml": (
                str(first["Body (HTML)"]) if not pd.isna(first["Body (HTML)"]) else ""
            ),
            "vendor": str(first["Vendor"]) if not pd.isna(first["Vendor"]) else "",
            "status": "DRAFT",
            "tags": tags,
            "productOptions": [
                *(
                    [
                        {
                            "name": "Färg",
                            "values": [{"name": value} for value in colors],
                        }
                    ]
                    if has_color
                    else []
                ),
                *(
                    [
                        {
                            "name": "Storlek",
                            "values": [{"name": value} for value in sizes],
                        }
                    ]
                    if has_size
                    else []
                ),
            ],
        }

        variants = [
            _variant_payload(
                row,
                has_color=has_color,
                has_size=has_size,
            )
            for _, row in group.iterrows()
        ]

        image_urls: list[str] = []
        for image_cell in group["Image URLs"].fillna(""):
            for url in str(image_cell).split(";"):
                url = url.strip()
                if url and url not in image_urls:
                    image_urls.append(url)

        collection_status = str(first.get("Collection Mapping Status", ""))
        collection = first.get("Suggested Collection", "")
        if pd.isna(collection):
            collection = ""

        plans.append(
            DJCreatePlan(
                handle=str(handle),
                product_create=product_create,
                initial_variant=variants[0],
                additional_variants=variants[1:],
                suggested_collection=str(collection),
                collection_mapping_status=collection_status,
                image_urls=image_urls,
            )
        )

    return plans


def save_dj_create_plans(
    plans: list[DJCreatePlan],
    output_path: Path,
) -> Path:
    """Save the create plan as JSONL for inspection; no Shopify writes."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        for plan in plans:
            record = {
                "handle": plan.handle,
                "product_create": plan.product_create,
                "initial_variant": plan.initial_variant,
                "additional_variants": plan.additional_variants,
                "suggested_collection": plan.suggested_collection,
                "collection_mapping_status": plan.collection_mapping_status,
                "image_urls": plan.image_urls,
            }
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    return output_path
