from dataclasses import dataclass
from pathlib import Path

from lxml import etree


@dataclass
class ProductFeedSummary:
    """Summary statistics from a supplier product feed."""

    product_count: int
    variant_count: int


def read_product_feed(file_path: Path) -> ProductFeedSummary:
    """
    Read an XML product feed and count products and variants.

    The parser uses iterparse so that large XML files can be processed
    without loading the entire documents into memory.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Product feed not found: {file_path}")

    if file_path.suffix.lower() != ".xml":
        raise ValueError("The product feed must be an XML file.")

    product_count = 0
    variant_count = 0

    try:
        context = etree.iterparse(
            str(file_path),
            events=("end",),
            recover=False,
            huge_tree=True,
        )

        for _, element in context:
            tag_name = etree.QName(element).localname.lower()

            if tag_name in {"product", "item"}:
                product_count += 1

            elif tag_name in {"variant", "sku"}:
                variant_count += 1

            element.clear()

            while element.getprevious() is not None:
                del element.getparent()[0]

    except etree.XMLSyntaxError as error:
        raise ValueError(f"Invalid XML product feed: {error}") from error

    return ProductFeedSummary(
        product_count=product_count,
        variant_count=variant_count,
    )
