import os

import requests
from dotenv import load_dotenv

load_dotenv()

SHOPIFY_CLIENT_ID = os.getenv("SHOPIFY_CLIENT_ID")
SHOPIFY_CLIENT_SECRET = os.getenv("SHOPIFY_CLIENT_SECRET")

print("Client ID loaded:", bool(SHOPIFY_CLIENT_ID))
print("Client secret loaded:", bool(SHOPIFY_CLIENT_SECRET))


SHOPIFY_SHOP = os.getenv("SHOPIFY_SHOP")

token_url = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/oauth/access_token"

response = requests.post(
    token_url,
    data={
        "grant_type": "client_credentials",
        "client_id": SHOPIFY_CLIENT_ID,
        "client_secret": SHOPIFY_CLIENT_SECRET,
    },
    timeout=30,
)

print("HTTP status:", response.status_code)

data = response.json()

print("Access token received:", bool(data.get("access_token")))
print("Scopes:", data.get("scope"))
print("Expires in:", data.get("expires_in"))


access_token = data["access_token"]

graphql_url = f"https://{SHOPIFY_SHOP}.myshopify.com/admin/api/2026-07/graphql.json"

query = """
query {
  products(first: 5) {
    nodes {
      id
      title
      handle
    }
  }
}
"""

response = requests.post(
    graphql_url,
    headers={
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    },
    json={"query": query},
    timeout=30,
)

print("GraphQL HTTP status:", response.status_code)
print(response.json())


mutation = """
mutation ProductCreate($product: ProductCreateInput!) {
  productCreate(product: $product) {
    product {
      id
      title
      handle
    }
    userErrors {
      field
      message
    }
  }
}
"""

variables = {"product": {"title": "API Sync Test Product", "status": "DRAFT"}}

response = requests.post(
    graphql_url,
    headers={
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    },
    json={
        "query": mutation,
        "variables": variables,
    },
    timeout=30,
)

print("Create product status:", response.status_code)
print(response.json())


product_id = "gid://shopify/Product/15752906178908"

mutation = """
mutation CreateOptions(
  $productId: ID!,
  $options: [OptionCreateInput!]!
) {
  productOptionsCreate(
    productId: $productId,
    options: $options
  ) {
    product {
      id
      options {
        id
        name
        values
      }
      variants(first: 10) {
        nodes {
          id
          title
          selectedOptions {
            name
            value
          }
        }
      }
    }
    userErrors {
      field
      message
      code
    }
  }
}
"""

variables = {
    "productId": product_id,
    "options": [
        {
            "name": "Färg",
            "values": [
                {"name": "Blå"},
                {"name": "Grön"},
            ],
        },
        {
            "name": "Storlek",
            "values": [
                {"name": "M"},
                {"name": "L"},
                {"name": "XL"},
            ],
        },
    ],
}

response = requests.post(
    graphql_url,
    headers={
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    },
    json={
        "query": mutation,
        "variables": variables,
    },
    timeout=30,
)

print("Create options status:", response.status_code)
print(response.json())


mutation = """
mutation ProductVariantsBulkCreate(
  $productId: ID!,
  $variants: [ProductVariantsBulkInput!]!
) {
  productVariantsBulkCreate(
    productId: $productId,
    variants: $variants
  ) {
    productVariants {
      id
      title
      selectedOptions {
        name
        value
      }
    }
    userErrors {
      field
      message
    }
  }
}
"""

variables = {
    "productId": product_id,
    "variants": [
        {
            "optionValues": [
                {"name": "Grön", "optionName": "Färg"},
                {"name": "M", "optionName": "Storlek"},
            ]
        },
        {
            "optionValues": [
                {"name": "Blå", "optionName": "Färg"},
                {"name": "L", "optionName": "Storlek"},
            ]
        },
        {
            "optionValues": [
                {"name": "Grön", "optionName": "Färg"},
                {"name": "L", "optionName": "Storlek"},
            ]
        },
        {
            "optionValues": [
                {"name": "Blå", "optionName": "Färg"},
                {"name": "XL", "optionName": "Storlek"},
            ]
        },
        {
            "optionValues": [
                {"name": "Grön", "optionName": "Färg"},
                {"name": "XL", "optionName": "Storlek"},
            ]
        },
    ],
}

response = requests.post(
    graphql_url,
    headers={
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    },
    json={
        "query": mutation,
        "variables": variables,
    },
    timeout=30,
)

print("Create variants status:", response.status_code)
print(response.json())


# DELETE

mutation = """
mutation DeleteVariant(
  $productId: ID!,
  $variantsIds: [ID!]!
) {
  productVariantsBulkDelete(
    productId: $productId,
    variantsIds: $variantsIds
  ) {
    product {
      id
      title
    }
    userErrors {
      field
      message
    }
  }
}
"""

variables = {
    "productId": product_id,
    "variantsIds": ["gid://shopify/ProductVariant/58676745044316"],
}

response = requests.post(
    graphql_url,
    headers={
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    },
    json={
        "query": mutation,
        "variables": variables,
    },
    timeout=30,
)

print("Delete variant status:", response.status_code)
print(response.json())


query = """
query ProductVariants($id: ID!) {
  product(id: $id) {
    id
    title
    variants(first: 20) {
      nodes {
        id
        title
        selectedOptions {
          name
          value
        }
      }
    }
  }
}
"""

response = requests.post(
    graphql_url,
    headers={
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    },
    json={
        "query": query,
        "variables": {"id": product_id},
    },
    timeout=30,
)

print("Verify variants status:", response.status_code)
print(response.json())


## UPDATE

mutation = """
mutation UpdateVariant(
  $productId: ID!,
  $variants: [ProductVariantsBulkInput!]!
) {
  productVariantsBulkUpdate(
    productId: $productId,
    variants: $variants
  ) {
    productVariants {
      id
      title
      price
      sku
      barcode
    }
    userErrors {
      field
      message
    }
  }
}
"""

variables = {
    "productId": product_id,
    "variants": [
        {
            "id": "gid://shopify/ProductVariant/58676713029980",
            "barcode": "7332515659934",
        }
    ],
}

response = requests.post(
    graphql_url,
    headers={
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    },
    json={
        "query": mutation,
        "variables": variables,
    },
    timeout=30,
)

print("Update EAN status:", response.status_code)
print(response.json())


mutation = """
mutation DeleteGreenVariants(
  $productId: ID!,
  $variantsIds: [ID!]!
) {
  productVariantsBulkDelete(
    productId: $productId,
    variantsIds: $variantsIds
  ) {
    product {
      id
      title
    }
    userErrors {
      field
      message
    }
  }
}
"""

variables = {
    "productId": product_id,
    "variantsIds": [
        "gid://shopify/ProductVariant/58676744946012",  # Grön / M
        "gid://shopify/ProductVariant/58676745011548",  # Grön / L
        "gid://shopify/ProductVariant/58676745077084",  # Grön / XL
    ],
}

response = requests.post(
    graphql_url,
    headers={
        "X-Shopify-Access-Token": access_token,
        "Content-Type": "application/json",
    },
    json={
        "query": mutation,
        "variables": variables,
    },
    timeout=30,
)

print("Delete green variants status:", response.status_code)
print(response.json())
