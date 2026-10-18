from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json

from ecommerce_product_importer.services.dj_shopify_create_plan import (
    DJCreatePlan,
)


PRODUCT_CREATE_MUTATION = """
mutation ProductCreate($product: ProductCreateInput!) {
  productCreate(product: $product) {
    product {
      id
      handle
      status
      variants(first: 1) {
        nodes {
          id
        }
      }
    }
    userErrors {
      field
      message
    }
  }
}
""".strip()


INITIAL_VARIANT_UPDATE_MUTATION = """
mutation ProductVariantsBulkUpdate(
  $productId: ID!,
  $variants: [ProductVariantsBulkInput!]!
) {
  productVariantsBulkUpdate(
    productId: $productId,
    variants: $variants
  ) {
    productVariants {
      id
      price
    }
    userErrors {
      field
      message
    }
  }
}
""".strip()


ADDITIONAL_VARIANTS_CREATE_MUTATION = """
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
      price
    }
    userErrors {
      field
      message
    }
  }
}
""".strip()


@dataclass(frozen=True)
class DJMutationOperation:
    """One planned Shopify mutation. It is never executed by this module."""

    handle: str
    step: int
    mutation_name: str
    query: str
    variables: dict
    depends_on: str | None = None


def build_dj_mutation_plan(
    create_plans: list[DJCreatePlan],
) -> list[DJMutationOperation]:
    """
    Convert D&J create plans into an ordered, read-only mutation plan.

    Runtime IDs are represented by placeholders. No network request is made.
    """
    operations: list[DJMutationOperation] = []

    for plan in create_plans:
        create_key = f"{plan.handle}:productCreate"

        operations.append(
            DJMutationOperation(
                handle=plan.handle,
                step=1,
                mutation_name="productCreate",
                query=PRODUCT_CREATE_MUTATION,
                variables={"product": plan.product_create},
            )
        )

        initial_variant = dict(plan.initial_variant)
        initial_variant["id"] = "$INITIAL_VARIANT_ID"

        operations.append(
            DJMutationOperation(
                handle=plan.handle,
                step=2,
                mutation_name="productVariantsBulkUpdate",
                query=INITIAL_VARIANT_UPDATE_MUTATION,
                variables={
                    "productId": "$PRODUCT_ID",
                    "variants": [initial_variant],
                },
                depends_on=create_key,
            )
        )

        if plan.additional_variants:
            operations.append(
                DJMutationOperation(
                    handle=plan.handle,
                    step=3,
                    mutation_name="productVariantsBulkCreate",
                    query=ADDITIONAL_VARIANTS_CREATE_MUTATION,
                    variables={
                        "productId": "$PRODUCT_ID",
                        "variants": plan.additional_variants,
                    },
                    depends_on=create_key,
                )
            )

    return operations


def summarize_mutation_plan(
    operations: list[DJMutationOperation],
) -> dict[str, int]:
    """Count planned Shopify mutations without executing them."""
    summary = {
        "productCreate": 0,
        "productVariantsBulkUpdate": 0,
        "productVariantsBulkCreate": 0,
    }

    for operation in operations:
        if operation.mutation_name in summary:
            summary[operation.mutation_name] += 1

    return summary


def save_dj_mutation_plan(
    operations: list[DJMutationOperation],
    output_path: Path,
) -> Path:
    """Save the dry-run mutation plan as JSONL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        for operation in operations:
            file.write(
                json.dumps(
                    asdict(operation),
                    ensure_ascii=False,
                )
                + "\n"
            )

    return output_path
