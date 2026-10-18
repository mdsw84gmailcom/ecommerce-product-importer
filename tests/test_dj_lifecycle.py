from datetime import date

from ecommerce_product_importer.models.lifecycle import LifecycleStatus
from ecommerce_product_importer.readers.dj_reader import DJProductRow
from ecommerce_product_importer.services.dj_lifecycle import (
    build_dj_product_lifecycle,
    evaluate_dj_row,
    evaluate_dj_rows,
)


TODAY = date(2026, 10, 18)


def make_row(
    *,
    tags: tuple[str, ...] = (),
    available_from: date | None = None,
    sku: str = "410000-99-0",
) -> DJProductRow:
    return DJProductRow(
        supplier="D&J",
        product_id="410000",
        product_name="Testprodukt",
        brand="Queen Anne",
        category="Test",
        description="Beskrivning",
        image_urls=(),
        main_image=None,
        recommended_price=499.0,
        dealer_price=199.0,
        gender=None,
        fit=None,
        material_technique=None,
        season=None,
        tags=tags,
        packaging_comment=None,
        presentation_date=None,
        color="Svart",
        color_code="99",
        sku=sku,
        size_code="0",
        size_name="One Size",
        ean="7393533000000",
        available_from=available_from,
    )


def test_build_dj_product_lifecycle_maps_supplier_fields() -> None:
    row = make_row(
        tags=("New", "Outlet"),
        available_from=date(2026, 10, 20),
    )

    lifecycle = build_dj_product_lifecycle(row)

    assert lifecycle.supplier == "D&J"
    assert lifecycle.product_id == "410000"
    assert lifecycle.variant_sku == "410000-99-0"
    assert lifecycle.supplier_tags == ("New", "Outlet")
    assert lifecycle.available_from == date(2026, 10, 20)


def test_evaluate_dj_new_row() -> None:
    evaluated = evaluate_dj_row(
        make_row(tags=("New",)),
        today=TODAY,
    )

    assert evaluated.lifecycle.has(LifecycleStatus.NEW)
    assert evaluated.lifecycle.shopify_tags == frozenset({"new"})


def test_evaluate_dj_outlet_row() -> None:
    evaluated = evaluate_dj_row(
        make_row(tags=("Outlet",)),
        today=TODAY,
    )

    assert evaluated.lifecycle.has(LifecycleStatus.SALE)
    assert evaluated.lifecycle.shopify_tags == frozenset({"sale"})


def test_evaluate_future_dj_row() -> None:
    evaluated = evaluate_dj_row(
        make_row(
            tags=("New",),
            available_from=date(2026, 10, 20),
        ),
        today=TODAY,
    )

    assert evaluated.lifecycle.statuses == frozenset(
        {LifecycleStatus.UPCOMING}
    )
    assert evaluated.lifecycle.shopify_tags == frozenset({"upcoming"})


def test_evaluate_dj_rows_keeps_all_variants() -> None:
    rows = [
        make_row(tags=("New",), sku="410000-99-S"),
        make_row(tags=("Outlet",), sku="410000-99-M"),
    ]

    evaluated = evaluate_dj_rows(rows, today=TODAY)

    assert len(evaluated) == 2
    assert evaluated[0].product.sku == "410000-99-S"
    assert evaluated[0].lifecycle.has(LifecycleStatus.NEW)
    assert evaluated[1].product.sku == "410000-99-M"
    assert evaluated[1].lifecycle.has(LifecycleStatus.SALE)
