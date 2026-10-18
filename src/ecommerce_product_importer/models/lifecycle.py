from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class LifecycleStatus(StrEnum):
    """Common lifecycle states used across suppliers."""

    ACTIVE = "ACTIVE"
    UPCOMING = "UPCOMING"
    NEW = "NEW"
    SALE = "SALE"
    SALE_ENDED = "SALE_ENDED"
    DISCONTINUED = "DISCONTINUED"


@dataclass(frozen=True)
class ProductLifecycle:
    """Supplier-independent lifecycle input for one product/variant."""

    supplier: str
    product_id: str
    variant_sku: str
    supplier_tags: tuple[str, ...] = ()
    available_from: date | None = None
    campaign_start: date | None = None
    campaign_end: date | None = None
    discontinued: bool = False


@dataclass(frozen=True)
class LifecycleResult:
    """Calculated lifecycle state and Shopify tags."""

    statuses: frozenset[LifecycleStatus]
    shopify_tags: frozenset[str]

    def has(self, status: LifecycleStatus) -> bool:
        return status in self.statuses
