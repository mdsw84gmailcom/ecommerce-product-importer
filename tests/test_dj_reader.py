from datetime import date
from pathlib import Path

import pytest
from openpyxl import Workbook

from ecommerce_product_importer.readers.dj_reader import read_dj_export


HEADERS = [
    "Product name (sv)",
    "Product number",
    "Brand",
    "Category (sv)",
    "Description (sv)",
    "Product images",
    "Main image",
    "Rek. ut",
    "ÅF-pris",
    "Gender (sv)",
    "Fit (sv)",
    "Material technique (sv)",
    "Season",
    "Tags",
    "Packaging Comment (sv)",
    "Presentation date",
    "Color (sv)",
    "Color code",
    "Description, Sku",
    "Description, Sku (en)",
    "Sku",
    "Size code",
    "Size name",
    "Ean",
    "Available from",
]


def write_export(path: Path, headers=HEADERS) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(headers)
    worksheet.append(
        [
            "Testprodukt",
            "410000",
            "Queen Anne",
            "Kök;Test",
            "En svensk beskrivning",
            "https://example.com/1.jpg,https://example.com/2.jpg",
            "https://example.com/1.jpg",
            499,
            199,
            "Unisex",
            None,
            "rPET",
            "AW26",
            "New;Outlet",
            "Presentkartong",
            date(2026, 9, 1),
            "Svart",
            "99",
            "Test SKU",
            "Test SKU EN",
            "410000-99-0",
            "0",
            "One Size",
            "7393533000000",
            date(2026, 10, 20),
        ]
    )
    workbook.save(path)


def test_read_dj_export_normalizes_row(tmp_path: Path) -> None:
    export_file = tmp_path / "dj.xlsx"
    write_export(export_file)

    rows = read_dj_export(export_file)

    assert len(rows) == 1
    row = rows[0]
    assert row.supplier == "D&J"
    assert row.product_id == "410000"
    assert row.sku == "410000-99-0"
    assert row.brand == "Queen Anne"
    assert row.category == "Kök;Test"
    assert row.recommended_price == 499.0
    assert row.dealer_price == 199.0
    assert row.image_urls == (
        "https://example.com/1.jpg",
        "https://example.com/2.jpg",
    )
    assert row.tags == ("New", "Outlet")
    assert row.presentation_date == date(2026, 9, 1)
    assert row.available_from == date(2026, 10, 20)
    assert row.ean == "7393533000000"


def test_read_dj_export_rejects_missing_required_columns(
    tmp_path: Path,
) -> None:
    export_file = tmp_path / "dj.xlsx"
    headers = [header for header in HEADERS if header != "Sku"]
    write_export(export_file, headers=headers)

    with pytest.raises(ValueError, match="Missing required D&J columns: Sku"):
        read_dj_export(export_file)


def test_read_dj_export_rejects_non_xlsx(tmp_path: Path) -> None:
    export_file = tmp_path / "dj.csv"
    export_file.write_text("test", encoding="utf-8")

    with pytest.raises(ValueError, match="must be an .xlsx file"):
        read_dj_export(export_file)
