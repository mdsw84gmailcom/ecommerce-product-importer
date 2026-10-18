from datetime import date

from ecommerce_product_importer.models.lifecycle import (
    LifecycleStatus,
    ProductLifecycle,
)
from ecommerce_product_importer.services.lifecycle_service import (
    evaluate_lifecycle,
)


TODAY = date(2026, 10, 18)


def make_lifecycle(**overrides) -> ProductLifecycle:
    values = {
        "supplier": "D&J",
        "product_id": "410000",
        "variant_sku": "410000-99-0",
    }
    values.update(overrides)
    return ProductLifecycle(**values)


def test_active_product() -> None:
    result = evaluate_lifecycle(make_lifecycle(), today=TODAY)
    assert result.statuses == frozenset({LifecycleStatus.ACTIVE})
    assert result.shopify_tags == frozenset()


def test_dj_new_tag_maps_to_new() -> None:
    result = evaluate_lifecycle(
        make_lifecycle(supplier_tags=("New",)),
        today=TODAY,
    )
    assert result.has(LifecycleStatus.NEW)
    assert result.shopify_tags == frozenset({"new"})


def test_dj_outlet_tag_maps_to_sale() -> None:
    result = evaluate_lifecycle(
        make_lifecycle(supplier_tags=("Outlet",)),
        today=TODAY,
    )
    assert result.has(LifecycleStatus.SALE)
    assert result.shopify_tags == frozenset({"sale"})


def test_product_can_be_new_and_sale() -> None:
    result = evaluate_lifecycle(
        make_lifecycle(supplier_tags=("New", "Outlet")),
        today=TODAY,
    )
    assert result.statuses == frozenset(
        {LifecycleStatus.NEW, LifecycleStatus.SALE}
    )
    assert result.shopify_tags == frozenset({"new", "sale"})


def test_future_available_from_is_upcoming() -> None:
    result = evaluate_lifecycle(
        make_lifecycle(
            supplier_tags=("New",),
            available_from=date(2026, 10, 20),
        ),
        today=TODAY,
    )
    assert result.statuses == frozenset({LifecycleStatus.UPCOMING})
    assert result.shopify_tags == frozenset({"upcoming"})


def test_available_today_can_be_new() -> None:
    result = evaluate_lifecycle(
        make_lifecycle(
            supplier_tags=("New",),
            available_from=TODAY,
        ),
        today=TODAY,
    )
    assert result.has(LifecycleStatus.NEW)
    assert "new" in result.shopify_tags


def test_campaign_in_date_range_is_sale() -> None:
    result = evaluate_lifecycle(
        make_lifecycle(
            campaign_start=date(2026, 10, 1),
            campaign_end=date(2026, 10, 31),
        ),
        today=TODAY,
    )
    assert result.has(LifecycleStatus.SALE)
    assert "sale" in result.shopify_tags


def test_future_campaign_is_not_sale_yet() -> None:
    result = evaluate_lifecycle(
        make_lifecycle(
            campaign_start=date(2026, 11, 1),
            campaign_end=date(2026, 11, 30),
        ),
        today=TODAY,
    )
    assert result.statuses == frozenset({LifecycleStatus.ACTIVE})
    assert "sale" not in result.shopify_tags


def test_expired_campaign_is_sale_ended() -> None:
    result = evaluate_lifecycle(
        make_lifecycle(
            campaign_start=date(2026, 10, 1),
            campaign_end=date(2026, 10, 17),
        ),
        today=TODAY,
    )
    assert result.has(LifecycleStatus.SALE_ENDED)
    assert "sale" not in result.shopify_tags


def test_discontinued_takes_precedence() -> None:
    result = evaluate_lifecycle(
        make_lifecycle(
            supplier_tags=("New", "Outlet"),
            discontinued=True,
        ),
        today=TODAY,
    )
    assert result.statuses == frozenset({LifecycleStatus.DISCONTINUED})
    assert result.shopify_tags == frozenset()
