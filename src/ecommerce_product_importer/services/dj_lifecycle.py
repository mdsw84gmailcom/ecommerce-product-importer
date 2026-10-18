from dataclasses import dataclass
from datetime import date

from ecommerce_product_importer.models.lifecycle import (
    LifecycleResult,
    ProductLifecycle,
)
from ecommerce_product_importer.readers.dj_reader import DJProductRow
from ecommerce_product_importer.services.lifecycle_service import (
    evaluate_lifecycle,
)


@dataclass(frozen=True)
class EvaluatedDJProductRow:
    """D&J product row together with its common lifecycle result."""

    product: DJProductRow
    lifecycle: LifecycleResult


def build_dj_product_lifecycle(row: DJProductRow) -> ProductLifecycle:
    """Map one normalized D&J row to the supplier-independent lifecycle model."""
    return ProductLifecycle(
        supplier=row.supplier,
        product_id=row.product_id,
        variant_sku=row.sku,
        supplier_tags=row.tags,
        available_from=row.available_from,
    )


def evaluate_dj_row(
    row: DJProductRow,
    *,
    today: date | None = None,
) -> EvaluatedDJProductRow:
    """Evaluate lifecycle state for one normalized D&J row."""
    lifecycle = build_dj_product_lifecycle(row)
    result = evaluate_lifecycle(lifecycle, today=today)

    return EvaluatedDJProductRow(
        product=row,
        lifecycle=result,
    )


def evaluate_dj_rows(
    rows: list[DJProductRow],
    *,
    today: date | None = None,
) -> list[EvaluatedDJProductRow]:
    """Evaluate lifecycle state for all D&J rows."""
    return [
        evaluate_dj_row(row, today=today)
        for row in rows
    ]
