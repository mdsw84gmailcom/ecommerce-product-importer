from pathlib import Path
import re

import pandas as pd

from ecommerce_product_importer.services.dj_lifecycle import (
    EvaluatedDJProductRow,
)

PREVIEW_COLUMNS = [
    "Handle",
    "Title",
    "Body (HTML)",
    "Vendor",
    "Source Category",
    "Suggested Collection",
    "Collection Mapping Status",
    "Tags",
    "Option1 Name",
    "Option1 Value",
    "Option2 Name",
    "Option2 Value",
    "Variant SKU",
    "Variant Barcode",
    "Main Image",
    "Image URLs",
    "Supplier Dealer Price",
    "Supplier Recommended Price",
    "Proposed Shopify Price",
    "Shopify Price",
    "Price Status",
]


CATEGORY_COLLECTION_MAP = {
    "Badrum": "Badrum",
    "Badrum;Badrock": "Badrockar",
    "Badrum;Badrumsmatta": "Badrumsmattor",
    "Badrum;Duschdraperi": "Duschdraperier",
    "Badrum;Frotté": "Handdukar & frotté",
    "Elektronik;Termometer": "Termometrar",
    "Flaskor;Termos": "Termosar",
    "Flaskor;Termosflaska": "Termosflaskor",
    "Flaskor;Vattenflaska": "Vattenflaskor",
    "Glas": "Glas",
    "Glas;Champagneglas": "Champagneglas",
    "Glas;Dricksglas": "Dricksglas",
    "Glas;Vinglas": "Vinglas",
    "Glas;Whiskeyglas": "Whiskeyglas",
    "Handskar;Kitchen glove": "Kökshandskar",
    "Handskar;Kök;Kitchen glove;Grillredskap": "Kökshandskar",
    "Inredning;Bordslampa": "Belysning",
    "Inredning;Duk": "Dukar",
    "Inredning;Ljuslykta": "Ljuslyktor",
    "Inredning;Ljusstake": "Ljusstakar",
    "Inredning;Pläd": "Plädar",
    "Kök": "Kök",
    "Kök;Förkläde": "Förkläden",
    "Kök;Grillredskap": "Grillredskap",
    "Kök;Gryta": "Grytor",
    "Kök;Grytlapp": "Grytlappar",
    "Kök;Kylväskor": "Kylväskor",
    "Kök;Kniv": "Knivar",
    "Kök;Kniv;Bestick": "Bestick",
    "Kök;Köksredskap": "Köksredskap",
    "Kök;Köksredskap;Kniv": "Knivar",
    "Kök;Kökshandduk": "Kökshanddukar",
    "Kök;Matlåda": "Matlådor",
    "Kök;Panna": "Stekpannor & pannor",
    "Kök;Picknick": "Picknick",
    "Kök;Pots": "Grytor",
    "Kök;Salt- och pepparkvarn": "Salt- & pepparkvarnar",
    "Kök;Servering": "Servering",
    "Kök;Skärbräda": "Skärbrädor",
    "Kök;Skärbräda;Kniv": "Skärbrädor",
    "Kök;Stekpanna": "Stekpannor & pannor",
    "Kök;Tallrik": "Tallrikar",
    "Kök;Termoskanna": "Termoskannor",
    "Kök;Ugnsform": "Ugnsformar",
    "Muggar;Bilmugg": "Termosmuggar",
    "Muggar;Kök;Serveringsfat;Mugg": "Muggar",
    "Muggar;Kök;Termosmugg;Mugg": "Termosmuggar",
    "Muggar;Mugg": "Muggar",
    "Muggar;Termosmugg": "Termosmuggar",
    "Paraply": "Paraplyer",
    "Set;Kök;Grillredskap": "Grillredskap",
    "Set;Kök;Serveringstillbehör": "Servering",
    "Skor;Toffla": "Tofflor",
    "Sovrum;Bäddset": "Bäddset",
    "Sovrum;Kudde": "Kuddar",
    "Sovrum;Kuddfodral": "Kuddfodral",
    "Sovrum;Necessär": "Necessärer",
    "Sovrum;Täcke": "Täcken",
    "Sovrum;Underlakan": "Lakan",
    "Spel & Lek;Spel": "Spel & lek",
    "Säkerhet;Brandbeständigt": "Säkerhet",
    "Säkerhet;Brandfilt": "Brandfiltar",
    "Säkerhet;Reflekterande": "Reflexer & säkerhet",
    "Säkerhet;Reflexväst": "Reflexvästar",
    "Textil;Badrum;Hamam;Badrock": "Badrockar",
    "Textil;Badrum;Strandbadlakan": "Strandhanddukar",
    "Textil;Hamam;Strandbadlakan": "Strandhanddukar",
    "Textil;Handduk": "Handdukar & frotté",
    "Textil;Picknick pläd": "Picknick",
    "Textil;Strandbadlakan": "Strandhanddukar",
    "Utomhusutrustning": "Utomhus",
    "Väskor": "Väskor",
    "Väskor;Datorväska": "Datorväskor",
    "Väskor;Dryckpåse": "Väskor",
    "Väskor;Korg": "Korgar",
    "Väskor;Kylväskor": "Kylväskor",
    "Väskor;Kök;Lunchkassar;Kylväskor": "Kylväskor",
    "Väskor;Lunchkassar": "Lunchväskor",
    "Väskor;Resväska": "Resväskor",
    "Väskor;Shoppingpåse": "Shoppingväskor",
    "Väskor;Textil;Hamam;Strandväska": "Strandväskor",
    "Väskor;Tygkassar": "Tygkassar",
    "Väskor;Tygkassar;Sportbag": "Sportväskor",
    "Väskor;Väska": "Väskor",
    "Väskor;Weekendväska": "Weekendväskor",
    "Överdelar;Poncho": "Ponchos",
}


def _suggest_collection(source_category: str) -> tuple[str, str]:
    category = source_category.strip()
    if not category:
        return "", "REVIEW_REQUIRED"

    collection = CATEGORY_COLLECTION_MAP.get(category)
    if collection is None:
        return "", "REVIEW_REQUIRED"

    return collection, "SUGGESTED"


def _slug(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def _unique_images(
    main_image: str | None,
    image_urls: tuple[str, ...],
) -> str:
    ordered: list[str] = []

    for image in (main_image, *image_urls):
        if image and image not in ordered:
            ordered.append(image)

    return ";".join(ordered)


def build_dj_shopify_preview(
    rows: list[EvaluatedDJProductRow],
) -> pd.DataFrame:
    """
    Map evaluated D&J rows to a Shopify-oriented review preview.

    D&J recommended retail price is ex VAT. Shopify stores the selling
    price incl. 25% VAT. Known source
    categories receive suggested collections; unknown categories stay
    REVIEW_REQUIRED. No Shopify API calls are made.
    """
    records: list[dict] = []

    for evaluated in rows:
        product = evaluated.product
        lifecycle = evaluated.lifecycle
        handle = f"dj-{_slug(product.product_id)}"
        suggested_collection, collection_status = _suggest_collection(product.category)

        records.append(
            {
                "Handle": handle,
                "Title": product.product_name,
                "Body (HTML)": product.description,
                "Vendor": product.brand,
                "Source Category": product.category,
                "Suggested Collection": suggested_collection,
                "Collection Mapping Status": collection_status,
                "Tags": ",".join(sorted(lifecycle.shopify_tags)),
                "Option1 Name": "Färg",
                "Option1 Value": product.color,
                "Option2 Name": "Storlek",
                "Option2 Value": product.size_name,
                "Variant SKU": product.sku,
                "Variant Barcode": product.ean or "",
                "Main Image": product.main_image or "",
                "Image URLs": _unique_images(
                    product.main_image,
                    product.image_urls,
                ),
                "Supplier Dealer Price": product.dealer_price,
                "Supplier Recommended Price": product.recommended_price,
                "Proposed Shopify Price": (
                    round(product.recommended_price * 1.25, 2)
                    if product.recommended_price is not None
                    else None
                ),
                "Shopify Price": (
                    round(product.recommended_price * 1.25, 2)
                    if product.recommended_price is not None
                    else None
                ),
                "Price Status": (
                    "READY"
                    if product.recommended_price is not None
                    else "REVIEW_REQUIRED"
                ),
            }
        )

    return pd.DataFrame(records, columns=PREVIEW_COLUMNS)


def save_dj_shopify_preview(
    rows: list[EvaluatedDJProductRow],
    output_path: Path,
) -> pd.DataFrame:
    """Save a local Shopify mapping preview and return the dataframe."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    dataframe = build_dj_shopify_preview(rows)
    dataframe.to_csv(
        output_path,
        index=False,
        encoding="utf-8-sig",
    )
    return dataframe
