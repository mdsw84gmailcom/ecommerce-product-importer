from datetime import date
from pathlib import Path

from ecommerce_product_importer.models.lifecycle import (
    LifecycleResult,
    LifecycleStatus,
)
from ecommerce_product_importer.readers.dj_reader import DJProductRow
from ecommerce_product_importer.services.dj_lifecycle import (
    EvaluatedDJProductRow,
)
from ecommerce_product_importer.services.dj_report import (
    build_dj_status_dataframe,
    save_dj_status_report,
    summarize_dj_statuses,
)


def make_evaluated(
    *,
    sku: str,
    statuses: frozenset[LifecycleStatus],
    shopify_tags: frozenset[str],
) -> EvaluatedDJProductRow:
    product = DJProductRow(
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
        tags=("New",),
        packaging_comment=None,
        presentation_date=None,
        color="Svart",
        color_code="99",
        sku=sku,
        size_code="0",
        size_name="One Size",
        ean="7393533000000",
        available_from=date(2026, 10, 18),
    )

    return EvaluatedDJProductRow(
        product=product,
        lifecycle=LifecycleResult(
            statuses=statuses,
            shopify_tags=shopify_tags,
        ),
    )


def test_build_dj_status_dataframe() -> None:
    rows = [
        make_evaluated(
            sku="410000-99-0",
            statuses=frozenset({LifecycleStatus.NEW}),
            shopify_tags=frozenset({"new"}),
        )
    ]

    dataframe = build_dj_status_dataframe(rows)

    assert len(dataframe) == 1
    assert dataframe.iloc[0]["sku"] == "410000-99-0"
    assert dataframe.iloc[0]["statuses"] == "NEW"
    assert dataframe.iloc[0]["shopify_tags"] == "new"


def test_summary_counts_multiple_statuses() -> None:
    rows = [
        make_evaluated(
            sku="A",
            statuses=frozenset(
                {LifecycleStatus.NEW, LifecycleStatus.SALE}
            ),
            shopify_tags=frozenset({"new", "sale"}),
        ),
        make_evaluated(
            sku="B",
            statuses=frozenset({LifecycleStatus.ACTIVE}),
            shopify_tags=frozenset(),
        ),
    ]

    summary = summarize_dj_statuses(rows)

    assert summary == {
        "ACTIVE": 1,
        "NEW": 1,
        "SALE": 1,
    }


def test_save_dj_status_report(tmp_path: Path) -> None:
    rows = [
        make_evaluated(
            sku="410000-99-0",
            statuses=frozenset({LifecycleStatus.NEW}),
            shopify_tags=frozenset({"new"}),
        )
    ]
    output = tmp_path / "reports" / "dj.csv"

    dataframe = save_dj_status_report(rows, output)

    assert output.exists()
    assert len(dataframe) == 1
