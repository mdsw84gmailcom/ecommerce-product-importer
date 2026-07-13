from pathlib import Path

from ecommerce_product_importer.readers import read_product_feed


def test_read_product_feed_counts_products_and_variants(tmp_path: Path) -> None:
    xml_content = """
    <catalog>
        <product>
            <variant />
            <variant />
        </product>
        <product>
            <variant />
        </product>
    </catalog>
    """

    xml_file = tmp_path / "product_feed.xml"
    xml_file.write_text(xml_content, encoding="utf-8")

    result = read_product_feed(xml_file)

    assert result.product_count == 2
    assert result.variant_count == 3
