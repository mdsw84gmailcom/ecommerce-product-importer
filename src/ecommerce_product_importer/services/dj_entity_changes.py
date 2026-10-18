from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd


ENTITY_CHANGE_COLUMNS = [
    "change_type",
    "product_id",
    "product_name",
    "color_code",
    "color",
]


def _text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _validate_report(name: str, frame: pd.DataFrame) -> None:
    required = {"product_id", "product_name", "color", "color_code"}
    missing = required - set(frame.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            f"Missing required columns in {name} report: {missing_text}"
        )


def _normalize_color_code(value) -> str:
    """Normalize numeric-looking supplier color codes such as 04, 4 and 4.0."""
    code = _text(value)
    if not code:
        return ""

    try:
        number = Decimal(code)
    except InvalidOperation:
        return code.casefold()

    if number == number.to_integral_value():
        return str(int(number))

    return code.casefold()


def _color_key(row: pd.Series) -> tuple[str, str]:
    product_id = _text(row["product_id"])
    color_code = _normalize_color_code(row["color_code"])
    color = _text(row["color"])

    # Prefer supplier color code when available, otherwise fall back to name.
    identity = color_code if color_code else color.casefold()
    return product_id, identity


def compare_dj_product_color_changes(
    previous: pd.DataFrame,
    current: pd.DataFrame,
) -> pd.DataFrame:
    """
    Detect product- and color-level additions/removals between D&J snapshots.

    This complements SKU-level comparison. It does not write to Shopify.
    """
    _validate_report("previous", previous)
    _validate_report("current", current)

    old_products = {
        _text(value)
        for value in previous["product_id"].dropna().tolist()
        if _text(value)
    }
    new_products = {
        _text(value)
        for value in current["product_id"].dropna().tolist()
        if _text(value)
    }

    old_colors: dict[tuple[str, str], dict[str, str]] = {}
    new_colors: dict[tuple[str, str], dict[str, str]] = {}

    for _, row in previous.iterrows():
        key = _color_key(row)
        if not key[0] or not key[1]:
            continue
        old_colors.setdefault(
            key,
            {
                "product_id": key[0],
                "product_name": _text(row["product_name"]),
                "color_code": _text(row["color_code"]),
                "color": _text(row["color"]),
            },
        )

    for _, row in current.iterrows():
        key = _color_key(row)
        if not key[0] or not key[1]:
            continue
        new_colors.setdefault(
            key,
            {
                "product_id": key[0],
                "product_name": _text(row["product_name"]),
                "color_code": _text(row["color_code"]),
                "color": _text(row["color"]),
            },
        )

    changes: list[dict] = []

    current_product_names = (
        current[["product_id", "product_name"]]
        .drop_duplicates(subset="product_id")
        .set_index("product_id")["product_name"]
        .to_dict()
    )
    previous_product_names = (
        previous[["product_id", "product_name"]]
        .drop_duplicates(subset="product_id")
        .set_index("product_id")["product_name"]
        .to_dict()
    )

    for product_id in sorted(new_products - old_products):
        changes.append(
            {
                "change_type": "NEW_PRODUCT",
                "product_id": product_id,
                "product_name": _text(current_product_names.get(product_id, "")),
                "color_code": "",
                "color": "",
            }
        )

    for product_id in sorted(old_products - new_products):
        changes.append(
            {
                "change_type": "REMOVED_PRODUCT",
                "product_id": product_id,
                "product_name": _text(previous_product_names.get(product_id, "")),
                "color_code": "",
                "color": "",
            }
        )

    for key in sorted(set(new_colors) - set(old_colors)):
        data = new_colors[key]
        # A brand new product already has a NEW_PRODUCT event; its colors are
        # still useful as explicit NEW_COLOR events for downstream planning.
        changes.append({"change_type": "NEW_COLOR", **data})

    for key in sorted(set(old_colors) - set(new_colors)):
        data = old_colors[key]
        changes.append({"change_type": "REMOVED_COLOR", **data})

    return pd.DataFrame(changes, columns=ENTITY_CHANGE_COLUMNS)


def summarize_dj_product_color_changes(
    changes: pd.DataFrame,
) -> dict[str, int]:
    if changes.empty:
        return {}

    counts = Counter(changes["change_type"].tolist())
    return dict(sorted(counts.items()))


def save_dj_product_color_changes(
    changes: pd.DataFrame,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    changes.to_csv(output_path, index=False, encoding="utf-8-sig")
