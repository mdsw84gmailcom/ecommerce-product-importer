import os
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

# --------------------------------------------------
# Environment
# --------------------------------------------------

load_dotenv(override=True)

auth_token = os.getenv("ABICART_AUTH_TOKEN")
webshop_id = os.getenv("ABICART_WEBSHOP_ID")

print("Token exists:", bool(auth_token))
print("Token length:", len(auth_token) if auth_token else 0)
print("Webshop ID:", webshop_id)

if not auth_token or not webshop_id:
    raise RuntimeError("Missing Abicart credentials in .env")

# --------------------------------------------------
# Load real Snickers supplier data
# --------------------------------------------------

SUPPLIER_FILE = Path("data/snickers/abicart/abicart_supplier_import.csv")

df = pd.read_csv(
    SUPPLIER_FILE,
    dtype={
        "Produktnummer": "string",
        "Produktnummer under kundens val": "string",
        "EAN": "string",
    },
)

product = df[df["Produktnummer"].astype("string").str.strip() == "1104"].copy()

if product.empty:
    raise RuntimeError("Model 1104 not found")

row = product.iloc[0]


# --------------------------------------------------
# Abicart connection
# --------------------------------------------------

url = "https://shop.textalk.se/backend/jsonrpc/v1/"

params = {
    "webshop": webshop_id,
    "auth": auth_token,
    "language": "sv",
}


# --------------------------------------------------
# Build article patch
# --------------------------------------------------

article_patch = {
    "articleNumber": str(row["Produktnummer"]),
    "name": {
        "sv": str(row["Produktens namn"]),
    },
    "introductionText": {
        "sv": str(row["Inledande text"]),
    },
    "description": {
        "sv": str(row["Beskrivning"]),
    },
    "price": {
        "regular": {
            "SEK": float(row["Pris (SEK)"]),
        }
    },
    "images": [
        str(row["Bild"]),
    ],
    # Existing choice from Abicart demo article:
    # Storlek -> M, L, XL
    "choiceOptions": {
        "19823740": [
            119971536,  # M
            119971538,  # L
            119971540,  # XL
        ]
    },
    "draft": True,
}


# --------------------------------------------------
# Validate new article
# IMPORTANT: Article.validate does NOT save anything
# --------------------------------------------------


payload = {
    "jsonrpc": "2.0",
    "method": "ArticleVariant.normalize",
    "params": [120296366, {}],
    "id": 1,
}


# --------------------------------------------------
# Send request
# --------------------------------------------------

response = requests.post(
    url,
    params=params,
    json=payload,
    timeout=30,
)

print("HTTP status:", response.status_code)
print("Response body:")
print(response.text)

response.raise_for_status()

data = response.json()


# --------------------------------------------------
# Show result
# --------------------------------------------------

print("Variant structure:")
print(data["result"])

if "error" in data:
    print("\nAPI error:")
    print(data["error"])
else:
    print("\nValidation result:")
    print(data["result"])

    if data["result"] == []:
        print("\nSUCCESS: Abicart accepted the article with choiceOptions.")
