from pathlib import Path

import pandas as pd

from ecommerce_product_importer.services.shopify_sync import (
    build_change_plan,
    build_shopify_variant_dataframe,
    compare_products,
    compare_variants,
)


def _prepare_dj_variant_input(preview: pd.DataFrame) -> pd.DataFrame:
    """Adapt the D&J preview to the generic Shopify variant comparator."""
    required = {
        "Variant SKU",
        "Shopify Price",
        "Variant Barcode",
        "Option1 Value",
        "Option2 Value",
    }
    missing = required - set(preview.columns)
    if missing:
        raise ValueError(
            "D&J preview is missing required columns: "
            + ", ".join(sorted(missing))
        )

    result = preview.copy()
    result["Variant Price"] = result["Shopify Price"]
    return result


def _filter_live_dj_products(live: pd.DataFrame) -> pd.DataFrame:
    """
    Restrict live Shopify data to products managed by the D&J importer.

    This prevents unrelated Shopify products from being reported as
    discontinued when comparing a D&J supplier export.
    """
    if live.empty:
        return live.copy()

    if "handle" not in live.columns:
        raise ValueError("Live Shopify dataframe is missing handle")

    return live[
        live["handle"].fillna("").astype(str).str.startswith("dj-")
    ].copy()


def build_dj_live_dry_run_plan(
    shopify_products: list[dict],
    preview: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, pd.DataFrame]]:
    """
    Compare a D&J import preview with live Shopify data without writing.

    Only live products with a dj- handle are included in the comparison.
    """
    live = build_shopify_variant_dataframe(shopify_products)
    live_dj = _filter_live_dj_products(live)
    new_variants = _prepare_dj_variant_input(preview)

    variant_comparison = compare_variants(live_dj, new_variants)
    product_comparison = compare_products(live_dj, preview)
    plan = build_change_plan(variant_comparison, product_comparison)

    return variant_comparison, product_comparison, plan


def save_dj_live_dry_run_reports(
    variant_comparison: pd.DataFrame,
    product_comparison: pd.DataFrame,
    reports_dir: Path,
) -> tuple[Path, Path]:
    """Save live Shopify comparison reports locally."""
    reports_dir.mkdir(parents=True, exist_ok=True)

    variant_path = reports_dir / "dj_shopify_live_variants.csv"
    product_path = reports_dir / "dj_shopify_live_products.csv"

    variant_comparison.to_csv(
        variant_path,
        index=False,
        encoding="utf-8-sig",
    )
    product_comparison.to_csv(
        product_path,
        index=False,
        encoding="utf-8-sig",
    )

    return variant_path, product_path


def summarize_plan(plan: dict[str, pd.DataFrame]) -> dict[str, int]:
    """Return compact counts for the generic Shopify change plan."""
    return {name: len(frame) for name, frame in plan.items()}
