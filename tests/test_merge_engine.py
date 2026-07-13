import pytest

from ecommerce_product_importer.models import Price, Product, Variant
from ecommerce_product_importer.services.merge_engine import (
    create_price_lookup,
    find_price,
    merge_product_variant_price,
)


def test_find_price_returns_matching_price() -> None:
    prices = [
        Price(
            model="1000",
            color="Black",
            size="M",
            net_price=500.0,
            recommended_price=899.0,
        )
    ]

    variant = Variant(
        article_number="1000-BLACK-M",
        model="1000",
        color="Black",
        size="M",
    )

    lookup = create_price_lookup(prices)
    result = find_price(variant, lookup)

    assert result is not None
    assert result.net_price == 500.0
    assert result.recommended_price == 899.0


def test_find_price_returns_none_when_price_is_missing() -> None:
    variant = Variant(
        article_number="1000-BLACK-L",
        model="1000",
        color="Black",
        size="L",
    )

    result = find_price(variant, {})

    assert result is None


def test_merge_product_variant_price_creates_catalog_product() -> None:
    product = Product(
        model="100",
        name="Work Trousers",
        brand="Example Brand",
        category="Workwear",
    )

    variant = Variant(
        article_number="1000-BLACK-M",
        model="1000",
        color="Black",
        size="M",
        image="https://example.com/image.jpg",
    )

    price = Price(
        model="1000",
        color="Black",
        size="M",
        net_price=500.0,
        recommended_price=899.0,
    )

    result = merge_product_variant_price(product, variant, price)

    assert result.article_number == "1000-BLACK-M"
    assert result.name == "Work Trousers"
    assert result.color == "Black"
    assert result.size == "M"
    assert result.net_price == 500.0
    assert result.recommended_price == 899, 0


def test_merge_raises_error_for_different_models() -> None:
    product = Product(
        model="100",
        name="Work Trousers",
        brand="Example Brand",
        category="Workwear",
    )

    variant = Variant(
        article_number="2000-BLACK-M",
        model="2000",
        color="Black",
        size="M",
    )

    price = Price(
        model="2000",
        color="Black",
        size="M",
        net_price=500.0,
        recommended_price=899.0,
    )

    with pytest.raises(
        ValueError,
        match="Product and variant model numbers do not match",
    ):
        merge_product_variant_price(product, variant, price)
