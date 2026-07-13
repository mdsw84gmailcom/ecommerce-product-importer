from ecommerce_product_importer.models import Price, Variant


def create_price_lookup(
    prices: list[Price],
) -> dict[tuple[str, str, str], Price]:
    """
    Create a lookup dictionary for fast price retrievel.

    Key:
        (model, color, size)
    """
    return {(price.model, price.color, price.size): price for price in prices}


def find_price(
    variant: Variant,
    lookup: dict[tuple[str, str, str], Price],
) -> Price | None:
    """
    Find the matching price for a variant.
    """
    key = (
        variant.model,
        variant.color,
        variant.size,
    )

    return lookup.get(key)
