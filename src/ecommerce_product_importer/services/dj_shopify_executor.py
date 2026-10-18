from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass

import requests

from ecommerce_product_importer.services.dj_shopify_mutation_plan import (
    DJMutationOperation,
)
from ecommerce_product_importer.services.shopify_sync import get_graphql_url


@dataclass(frozen=True)
class DJApplyResult:
    handle: str
    status: str
    product_id: str | None
    initial_variant_id: str | None
    completed_mutations: tuple[str, ...]


def _graphql(
    *,
    shop: str,
    access_token: str,
    query: str,
    variables: dict,
) -> dict:
    response = requests.post(
        get_graphql_url(shop),
        headers={
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": access_token,
        },
        json={
            "query": query,
            "variables": variables,
        },
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    if data.get("errors"):
        raise RuntimeError(f"Shopify GraphQL errors: {data['errors']}")

    return data["data"]


def _raise_user_errors(payload: dict, mutation_name: str) -> None:
    user_errors = payload.get("userErrors") or []
    if user_errors:
        raise RuntimeError(
            f"{mutation_name} userErrors: {user_errors}"
        )


def _resolve_runtime_variables(
    variables: dict,
    *,
    product_id: str | None,
    initial_variant_id: str | None,
) -> dict:
    resolved = deepcopy(variables)

    def replace(value):
        if isinstance(value, dict):
            return {key: replace(item) for key, item in value.items()}
        if isinstance(value, list):
            return [replace(item) for item in value]
        if value == "$PRODUCT_ID":
            if not product_id:
                raise RuntimeError("Product ID is not available yet")
            return product_id
        if value == "$INITIAL_VARIANT_ID":
            if not initial_variant_id:
                raise RuntimeError("Initial variant ID is not available yet")
            return initial_variant_id
        return value

    return replace(resolved)


def execute_dj_product_create(
    *,
    shop: str,
    access_token: str,
    operations: list[DJMutationOperation],
    handle: str,
    apply: bool = False,
) -> DJApplyResult:
    """
    Execute exactly one D&J product plan.

    Safety rules:
    - only one handle may be present
    - dry-run is the default
    - the product must be created as DRAFT
    - delete/publish mutations are rejected
    """
    selected = sorted(
        (operation for operation in operations if operation.handle == handle),
        key=lambda operation: operation.step,
    )

    if not selected:
        raise ValueError(f"No mutation plan found for handle {handle}")

    if any(operation.handle != handle for operation in selected):
        raise ValueError("Mutation plan contains more than one handle")

    mutation_names = [operation.mutation_name for operation in selected]

    if "productCreate" not in mutation_names:
        raise ValueError("Plan does not contain productCreate")

    if any(
        "Delete" in name or "Publish" in name or "Unpublish" in name
        for name in mutation_names
    ):
        raise ValueError("Delete/publish mutations are not allowed")

    create_operation = next(
        operation
        for operation in selected
        if operation.mutation_name == "productCreate"
    )
    product_input = create_operation.variables.get("product", {})
    if product_input.get("status") != "DRAFT":
        raise ValueError("Product creation must use DRAFT status")

    if not apply:
        return DJApplyResult(
            handle=handle,
            status="DRY_RUN",
            product_id=None,
            initial_variant_id=None,
            completed_mutations=tuple(),
        )

    product_id: str | None = None
    initial_variant_id: str | None = None
    completed: list[str] = []

    for operation in selected:
        variables = _resolve_runtime_variables(
            operation.variables,
            product_id=product_id,
            initial_variant_id=initial_variant_id,
        )
        data = _graphql(
            shop=shop,
            access_token=access_token,
            query=operation.query,
            variables=variables,
        )
        payload = data[operation.mutation_name]
        _raise_user_errors(payload, operation.mutation_name)

        if operation.mutation_name == "productCreate":
            product = payload.get("product")
            if not product:
                raise RuntimeError("productCreate did not return a product")

            if product.get("status") != "DRAFT":
                raise RuntimeError(
                    f"Created product status is {product.get('status')}, expected DRAFT"
                )

            product_id = product["id"]
            nodes = (product.get("variants") or {}).get("nodes") or []
            if len(nodes) != 1 or not nodes[0].get("id"):
                raise RuntimeError(
                    "productCreate did not return exactly one initial variant"
                )
            initial_variant_id = nodes[0]["id"]

        completed.append(operation.mutation_name)

    return DJApplyResult(
        handle=handle,
        status="CREATED_DRAFT",
        product_id=product_id,
        initial_variant_id=initial_variant_id,
        completed_mutations=tuple(completed),
    )
