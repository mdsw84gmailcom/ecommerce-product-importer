from collections import Counter
from pathlib import Path

import pandas as pd


CHANGE_COLUMNS = [
    "change_type",
    "sku",
    "product_id",
    "product_name",
    "old_color",
    "new_color",
    "old_size",
    "new_size",
    "old_dealer_price",
    "new_dealer_price",
    "old_recommended_price",
    "new_recommended_price",
    "old_statuses",
    "new_statuses",
    "old_shopify_tags",
    "new_shopify_tags",
]


def _normalize(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _normalize_price(value) -> float | None:
    if pd.isna(value) or value == "":
        return None
    return float(value)


def compare_dj_status_reports(
    previous: pd.DataFrame,
    current: pd.DataFrame,
) -> pd.DataFrame:
    """Compare two D&J status reports and return reviewable change rows."""
    required = {
        "sku",
        "product_id",
        "product_name",
        "color",
        "size",
        "dealer_price",
        "recommended_price",
        "statuses",
        "shopify_tags",
    }

    for name, frame in (("previous", previous), ("current", current)):
        missing = required - set(frame.columns)
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(
                f"Missing required columns in {name} report: {missing_text}"
            )

        if frame["sku"].duplicated().any():
            duplicates = frame.loc[frame["sku"].duplicated(), "sku"].tolist()
            raise ValueError(
                f"Duplicate SKU values in {name} report: {duplicates[:5]}"
            )

    old = previous.set_index("sku", drop=False)
    new = current.set_index("sku", drop=False)

    all_skus = sorted(set(old.index) | set(new.index))
    changes: list[dict] = []

    for sku in all_skus:
        old_row = old.loc[sku] if sku in old.index else None
        new_row = new.loc[sku] if sku in new.index else None

        if old_row is None:
            changes.append(
                _build_change_row("NEW_SKU", sku, None, new_row)
            )
            continue

        if new_row is None:
            changes.append(
                _build_change_row("REMOVED_SKU", sku, old_row, None)
            )
            continue

        old_dealer = _normalize_price(old_row["dealer_price"])
        new_dealer = _normalize_price(new_row["dealer_price"])
        old_rrp = _normalize_price(old_row["recommended_price"])
        new_rrp = _normalize_price(new_row["recommended_price"])

        if old_dealer != new_dealer or old_rrp != new_rrp:
            changes.append(
                _build_change_row("PRICE_CHANGED", sku, old_row, new_row)
            )

        if (
            _normalize(old_row["color"]) != _normalize(new_row["color"])
            or _normalize(old_row["size"]) != _normalize(new_row["size"])
        ):
            changes.append(
                _build_change_row("VARIANT_CHANGED", sku, old_row, new_row)
            )

        if _normalize(old_row["statuses"]) != _normalize(new_row["statuses"]):
            changes.append(
                _build_change_row("STATUS_CHANGED", sku, old_row, new_row)
            )

        if _normalize(old_row["shopify_tags"]) != _normalize(
            new_row["shopify_tags"]
        ):
            changes.append(
                _build_change_row("SHOPIFY_TAGS_CHANGED", sku, old_row, new_row)
            )

    return pd.DataFrame(changes, columns=CHANGE_COLUMNS)


def _build_change_row(
    change_type: str,
    sku: str,
    old_row,
    new_row,
) -> dict:
    source = new_row if new_row is not None else old_row

    return {
        "change_type": change_type,
        "sku": sku,
        "product_id": _normalize(source["product_id"]) if source is not None else "",
        "product_name": _normalize(source["product_name"]) if source is not None else "",
        "old_color": _normalize(old_row["color"]) if old_row is not None else "",
        "new_color": _normalize(new_row["color"]) if new_row is not None else "",
        "old_size": _normalize(old_row["size"]) if old_row is not None else "",
        "new_size": _normalize(new_row["size"]) if new_row is not None else "",
        "old_dealer_price": (
            _normalize_price(old_row["dealer_price"]) if old_row is not None else None
        ),
        "new_dealer_price": (
            _normalize_price(new_row["dealer_price"]) if new_row is not None else None
        ),
        "old_recommended_price": (
            _normalize_price(old_row["recommended_price"]) if old_row is not None else None
        ),
        "new_recommended_price": (
            _normalize_price(new_row["recommended_price"]) if new_row is not None else None
        ),
        "old_statuses": (
            _normalize(old_row["statuses"]) if old_row is not None else ""
        ),
        "new_statuses": (
            _normalize(new_row["statuses"]) if new_row is not None else ""
        ),
        "old_shopify_tags": (
            _normalize(old_row["shopify_tags"]) if old_row is not None else ""
        ),
        "new_shopify_tags": (
            _normalize(new_row["shopify_tags"]) if new_row is not None else ""
        ),
    }


def summarize_dj_changes(changes: pd.DataFrame) -> dict[str, int]:
    """Count change types in a D&J comparison report."""
    if changes.empty:
        return {}

    counts = Counter(changes["change_type"].tolist())
    return dict(sorted(counts.items()))


def save_dj_change_report(
    changes: pd.DataFrame,
    output_path: Path,
) -> None:
    """Save a D&J change report as UTF-8 CSV."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    changes.to_csv(output_path, index=False, encoding="utf-8-sig")
