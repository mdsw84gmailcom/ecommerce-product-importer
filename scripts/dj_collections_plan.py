from pathlib import Path

import pandas as pd

SOURCE = Path("data/dj/reports/dj_collections_preview.csv")
OUTPUT = Path("data/dj/reports/dj_collections_plan.csv")

COLLECTIONS = {
    "Kök & Matlagning": [
        "Kök",
        "Knivar",
        "Grytor",
        "Köksredskap",
        "Skärbrädor",
        "Stekpannor & pannor",
        "Förkläden",
        "Grytlappar",
        "Grillredskap",
        "Kökshanddukar",
        "Matlådor",
        "Ugnsformar",
        "Bestick",
        "Salt- & pepparkvarnar",
    ],
    "Glas & Servering": [
        "Glas",
        "Champagneglas",
        "Dricksglas",
        "Vinglas",
        "Whiskeyglas",
        "Muggar",
        "Servering",
        "Tallrikar",
    ],
    "Hem & Inredning": [
        "Belysning",
        "Dukar",
        "Ljuslyktor",
        "Ljusstakar",
        "Plädar",
    ],
    "Bad & Spa": [
        "Badrum",
        "Badrockar",
        "Badrumsmattor",
        "Duschdraperier",
        "Handdukar & frotté",
        "Strandhanddukar",
    ],
    "Sovrum & Textilier": [
        "Bäddset",
        "Kuddar",
        "Kuddfodral",
        "Täcken",
        "Lakan",
    ],
    "Väskor & Accessoarer": [
        "Väskor",
        "Datorväskor",
        "Korgar",
        "Lunchväskor",
        "Resväskor",
        "Shoppingväskor",
        "Strandväskor",
        "Tygkassar",
        "Sportväskor",
        "Weekendväskor",
        "Necessärer",
        "Paraplyer",
    ],
    "Friluftsliv & Fritid": [
        "Termosar",
        "Termosflaskor",
        "Vattenflaskor",
        "Termosmuggar",
        "Termoskannor",
        "Picknick",
        "Utomhus",
        "Kylväskor",
    ],
    "Spel & Lek": ["Spel & lek"],
}


def category_for(suggested):
    for category, collections in COLLECTIONS.items():
        if suggested in collections:
            return category
    return "REVIEW_REQUIRED"


def main():
    df = pd.read_csv(SOURCE)

    df["Target Collection"] = df["Suggested Collection"].apply(category_for)

    # Komplettera produkter utan leverantörskategori.
    overrides = {
        # Presentförpackningar
        "dj-411115": "Presentset & Gåvoset",
        "dj-43142304": "Presentset & Gåvoset",
        "dj-43142295": "Presentset & Gåvoset",
        "dj-43142299": "Presentset & Gåvoset",
        # Bad & Spa
        "dj-410931": "Bad & Spa",
        "dj-411010": "Bad & Spa",
        # Kök & Matlagning
        "dj-411267": "Kök & Matlagning",
        "dj-411131": "Kök & Matlagning",
        "dj-411219": "Kök & Matlagning",
        "dj-411377": "Kök & Matlagning",
        "dj-411375": "Kök & Matlagning",
        "dj-430913": "Kök & Matlagning",
        "dj-411395": "Kök & Matlagning",
        "dj-411392": "Kök & Matlagning",
        "dj-411393": "Kök & Matlagning",
        # Glas & Servering
        "dj-411379": "Glas & Servering",
        "dj-411378": "Glas & Servering",
        "dj-411400": "Glas & Servering",
        "dj-411280": "Glas & Servering",
        # Hem & Inredning
        "dj-411361": "Hem & Inredning",
        "dj-410764": "Hem & Inredning",
        "dj-410745": "Hem & Inredning",
        "dj-410717": "Hem & Inredning",
        "dj-410219": "Hem & Inredning",
        "dj-430904": "Hem & Inredning",
        "dj-411397": "Hem & Inredning",
        # Sovrum & Textilier
        "dj-411303": "Sovrum & Textilier",
        # Väskor & Accessoarer
        "dj-411368": "Väskor & Accessoarer",
        "dj-411369": "Väskor & Accessoarer",
        "dj-411367": "Väskor & Accessoarer",
        "dj-430903": "Väskor & Accessoarer",
        "dj-430915": "Väskor & Accessoarer",
        "dj-430907": "Väskor & Accessoarer",
        # Friluftsliv & Fritid
        "dj-411058swe": "Friluftsliv & Fritid",
        "dj-411305": "Friluftsliv & Fritid",
        "dj-430914": "Friluftsliv & Fritid",
        "dj-430906": "Friluftsliv & Fritid",
        "dj-430910": "Friluftsliv & Fritid",
        "dj-430905": "Friluftsliv & Fritid",
        "dj-430911": "Friluftsliv & Fritid",
        "dj-430909": "Friluftsliv & Fritid",
        "dj-430908": "Friluftsliv & Fritid",
        "dj-430912": "Friluftsliv & Fritid",
        "dj-411327": "Friluftsliv & Fritid",
        # Fritid och personlig säkerhet
        "dj-411180": "Friluftsliv & Fritid",
        "dj-411036": "Friluftsliv & Fritid",
        "dj-411174": "Friluftsliv & Fritid",
        "dj-411175": "Friluftsliv & Fritid",
        "dj-411277": "Friluftsliv & Fritid",
    }

    for handle, category in overrides.items():
        df.loc[df["Handle"] == handle, "Target Collection"] = category

    plan = df[["Handle", "Title", "Target Collection"]].drop_duplicates()

    plan.to_csv(OUTPUT, index=False, encoding="utf-8-sig")

    print(f"Products: {plan['Handle'].nunique()}")
    print("Collection assignments:")
    print(plan["Target Collection"].value_counts())
    print(
        f"Review required: {plan.loc[plan['Target Collection'] == 'REVIEW_REQUIRED', 'Handle'].nunique()}"
    )
    print(f"Report: {OUTPUT}")
    print("Shopify writes performed: 0")


if __name__ == "__main__":
    main()
