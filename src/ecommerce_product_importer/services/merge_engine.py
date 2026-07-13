from ecommerce_product_importer.models import (
    Price,
    Variant,
    Product,
    CatalogProduct,
)


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


def merge_product_variant_price(
    product: Product,
    variant: Variant,
    price: Price,
) -> CatalogProduct:
    """Combine product, variant and price data into one catalog row"""
    if product.model != variant.model:
        raise ValueError("Product and variant model numbers do not match.")

    if variant.model != price.model:
        raise ValueError("Variant and price model numbers do not match.")

    if variant.color != price.color:
        raise ValueError("Variant and price colors do not match.")

    if variant.size != price.size:
        raise ValueError("Variant and price sizes do not match")

    return CatalogProduct(
        article_number=variant.article_number,
        model=product.model,
        name=product.name,
        brand=product.brand,
        category=product.category,
        color=variant.color,
        size=variant.size,
        image=variant.image,
        net_price=price.net_price,
        recommended_price=price.recommended_price,
    )
