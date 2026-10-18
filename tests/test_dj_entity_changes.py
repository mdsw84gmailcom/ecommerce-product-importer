from pathlib import Path

import pandas as pd

from ecommerce_product_importer.services.dj_entity_changes import (
    compare_dj_product_color_changes,
    save_dj_product_color_changes,
    summarize_dj_product_color_changes,
)


def row(
    product_id: str,
    product_name: str,
    color: str,
    color_code: str,
) -> dict:
    return {
        "product_id": product_id,
        "product_name": product_name,
        "color": color,
        "color_code": color_code,
    }


def test_detects_new_and_removed_product() -> None:
    previous = pd.DataFrame([row("OLD", "Old", "Svart", "04")])
    current = pd.DataFrame([row("NEW", "New", "Blå", "56")])

    changes = compare_dj_product_color_changes(previous, current)

    assert "NEW_PRODUCT" in set(changes["change_type"])
    assert "REMOVED_PRODUCT" in set(changes["change_type"])


def test_detects_new_color_for_existing_product() -> None:
    previous = pd.DataFrame([row("A", "Test", "Svart", "04")])
    current = pd.DataFrame(
        [
            row("A", "Test", "Svart", "04"),
            row("A", "Test", "Blå", "56"),
        ]
    )

    changes = compare_dj_product_color_changes(previous, current)

    new_colors = changes[changes["change_type"] == "NEW_COLOR"]
    assert len(new_colors) == 1
    assert new_colors.iloc[0]["color"] == "Blå"


def test_color_name_fallback_when_code_missing() -> None:
    previous = pd.DataFrame([row("A", "Test", "Svart", "")])
    current = pd.DataFrame(
        [
            row("A", "Test", "Svart", ""),
            row("A", "Test", "Blå", ""),
        ]
    )

    changes = compare_dj_product_color_changes(previous, current)

    assert list(changes["change_type"]) == ["NEW_COLOR"]


def test_no_changes() -> None:
    previous = pd.DataFrame([row("A", "Test", "Svart", "04")])
    current = previous.copy()

    changes = compare_dj_product_color_changes(previous, current)

    assert changes.empty


def test_summary_and_save(tmp_path: Path) -> None:
    changes = pd.DataFrame(
        [
            {"change_type": "NEW_PRODUCT"},
            {"change_type": "NEW_COLOR"},
            {"change_type": "NEW_COLOR"},
        ]
    )
    assert summarize_dj_product_color_changes(changes) == {
        "NEW_COLOR": 2,
        "NEW_PRODUCT": 1,
    }

    output = tmp_path / "entities.csv"
    save_dj_product_color_changes(changes, output)
    assert output.exists()
