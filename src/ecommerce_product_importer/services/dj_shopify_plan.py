from collections import Counter
from pathlib import Path

import pandas as pd


PLAN_COLUMNS = [
    "action",
    "risk",
    "auto_apply_allowed",
    "sku",
    "product_id",
    "product_name",
    "reason",
    "old_value",
    "new_value",
]


def _text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def build_dj_shopify_dry_run_plan(
    changes: pd.DataFrame,
) -> pd.DataFrame:
    """
    Convert D&J change rows into a read-only Shopify action plan.

    The function never calls Shopify and never mutates store data.
    Destructive or commercially sensitive changes are marked for review.
    """
    required = {
        "change_type",
        "sku",
        "product_id",
        "product_name",
        "old_dealer_price",
        "new_dealer_price",
        "old_recommended_price",
        "new_recommended_price",
        "old_statuses",
        "new_statuses",
        "old_shopify_tags",
        "new_shopify_tags",
    }

    missing = required - set(changes.columns)
    if missing:
        missing_text = ", ".join(sorted(missing))
        raise ValueError(
            f"Missing required D&J change columns: {missing_text}"
        )

    actions: list[dict] = []

    for _, row in changes.iterrows():
        change_type = _text(row["change_type"])
        common = {
            "sku": _text(row["sku"]),
            "product_id": _text(row["product_id"]),
            "product_name": _text(row["product_name"]),
        }

        if change_type == "NEW_SKU":
            actions.append(
                {
                    **common,
                    "action": "CREATE_OR_REVIEW_VARIANT",
                    "risk": "MEDIUM",
                    "auto_apply_allowed": False,
                    "reason": "Supplier export contains a new SKU.",
                    "old_value": "",
                    "new_value": common["sku"],
                }
            )

        elif change_type == "REMOVED_SKU":
            actions.append(
                {
                    **common,
                    "action": "REVIEW_REMOVAL",
                    "risk": "HIGH",
                    "auto_apply_allowed": False,
                    "reason": (
                        "SKU disappeared from the supplier export. "
                        "Do not remove it from Shopify automatically."
                    ),
                    "old_value": common["sku"],
                    "new_value": "",
                }
            )

        elif change_type == "PRICE_CHANGED":
            old_value = (
                f"dealer={_text(row['old_dealer_price'])}; "
                f"recommended={_text(row['old_recommended_price'])}"
            )
            new_value = (
                f"dealer={_text(row['new_dealer_price'])}; "
                f"recommended={_text(row['new_recommended_price'])}"
            )
            actions.append(
                {
                    **common,
                    "action": "REVIEW_PRICE_UPDATE",
                    "risk": "HIGH",
                    "auto_apply_allowed": False,
                    "reason": (
                        "Supplier pricing changed. Shopify selling price "
                        "must be calculated by the store pricing rules "
                        "before any update."
                    ),
                    "old_value": old_value,
                    "new_value": new_value,
                }
            )

        elif change_type == "VARIANT_CHANGED":
            actions.append(
                {
                    **common,
                    "action": "REVIEW_VARIANT_UPDATE",
                    "risk": "MEDIUM",
                    "auto_apply_allowed": False,
                    "reason": "Color or size changed for an existing SKU.",
                    "old_value": "",
                    "new_value": "",
                }
            )

        elif change_type == "STATUS_CHANGED":
            actions.append(
                {
                    **common,
                    "action": "REVIEW_LIFECYCLE_UPDATE",
                    "risk": "LOW",
                    "auto_apply_allowed": False,
                    "reason": "Lifecycle status changed.",
                    "old_value": _text(row["old_statuses"]),
                    "new_value": _text(row["new_statuses"]),
                }
            )

        elif change_type == "SHOPIFY_TAGS_CHANGED":
            actions.append(
                {
                    **common,
                    "action": "UPDATE_LIFECYCLE_TAGS",
                    "risk": "LOW",
                    "auto_apply_allowed": True,
                    "reason": (
                        "Only managed lifecycle tags are changing "
                        "(new, sale, upcoming)."
                    ),
                    "old_value": _text(row["old_shopify_tags"]),
                    "new_value": _text(row["new_shopify_tags"]),
                }
            )

        else:
            actions.append(
                {
                    **common,
                    "action": "REVIEW_UNKNOWN_CHANGE",
                    "risk": "HIGH",
                    "auto_apply_allowed": False,
                    "reason": f"Unsupported change type: {change_type}",
                    "old_value": "",
                    "new_value": "",
                }
            )

    return pd.DataFrame(actions, columns=PLAN_COLUMNS)


def summarize_dj_shopify_plan(
    plan: pd.DataFrame,
) -> dict[str, int]:
    """Count proposed Shopify actions."""
    if plan.empty:
        return {}

    counts = Counter(plan["action"].tolist())
    return dict(sorted(counts.items()))


def save_dj_shopify_dry_run_plan(
    plan: pd.DataFrame,
    output_path: Path,
) -> None:
    """Save the read-only Shopify plan locally."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plan.to_csv(output_path, index=False, encoding="utf-8-sig")
