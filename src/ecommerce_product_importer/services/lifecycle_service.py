from datetime import date

from ecommerce_product_importer.models.lifecycle import (
    LifecycleResult,
    LifecycleStatus,
    ProductLifecycle,
)


NEW_TAGS = {"new", "ny", "nyhet"}
SALE_TAGS = {"outlet", "sale", "rea", "campaign", "kampanj"}


def _normalized_tags(tags: tuple[str, ...]) -> set[str]:
    return {tag.strip().casefold() for tag in tags if tag.strip()}


def evaluate_lifecycle(
    lifecycle: ProductLifecycle,
    *,
    today: date | None = None,
) -> LifecycleResult:
    """
    Calculate common lifecycle states without changing Shopify.

    Multiple states may be active at the same time, for example NEW + SALE.
    DISCONTINUED takes precedence over all other states.
    """
    current_date = today or date.today()
    tags = _normalized_tags(lifecycle.supplier_tags)

    if lifecycle.discontinued:
        return LifecycleResult(
            statuses=frozenset({LifecycleStatus.DISCONTINUED}),
            shopify_tags=frozenset(),
        )

    if (
        lifecycle.available_from is not None
        and lifecycle.available_from > current_date
    ):
        return LifecycleResult(
            statuses=frozenset({LifecycleStatus.UPCOMING}),
            shopify_tags=frozenset({"upcoming"}),
        )

    statuses: set[LifecycleStatus] = set()
    shopify_tags: set[str] = set()

    if tags & NEW_TAGS:
        statuses.add(LifecycleStatus.NEW)
        shopify_tags.add("new")

    supplier_marks_sale = bool(tags & SALE_TAGS)
    campaign_has_started = (
        lifecycle.campaign_start is None
        or lifecycle.campaign_start <= current_date
    )
    campaign_has_ended = (
        lifecycle.campaign_end is not None
        and lifecycle.campaign_end < current_date
    )
    campaign_is_configured = (
        lifecycle.campaign_start is not None
        or lifecycle.campaign_end is not None
    )

    if campaign_has_ended:
        statuses.add(LifecycleStatus.SALE_ENDED)
    elif supplier_marks_sale or (
        campaign_is_configured and campaign_has_started
    ):
        statuses.add(LifecycleStatus.SALE)
        shopify_tags.add("sale")

    if not statuses:
        statuses.add(LifecycleStatus.ACTIVE)

    return LifecycleResult(
        statuses=frozenset(statuses),
        shopify_tags=frozenset(shopify_tags),
    )
