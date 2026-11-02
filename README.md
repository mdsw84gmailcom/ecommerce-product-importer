# E-commerce Product Importer

A Python data-engineering project for preparing supplier catalogs and safely synchronizing products with Shopify. Developed first for **Snickers Workwear**, then extended with a **D&J** supplier adapter.

The goal is a repeatable workflow: read supplier data, normalize and validate it, compare it with the existing Shopify catalog, review proposed changes, and apply approved updates.

## How it works

```text
Supplier files (Excel / XML / images)
                  |
            Source readers
                  |
        Validation and mapping
                  |
         Shopify-ready catalog
                  |
       Live catalog comparison
                  |
         Review / dry run
                  |
        Approved Shopify writes
```

Shopify integration and catalog-processing logic live in `src/ecommerce_product_importer/`. Supplier-specific parsing and business rules are kept separate so that a new supplier does not require rewriting the entire pipeline.

## Suppliers

### Snickers Workwear

The original implementation combines an Excel price list, an XML product feed, images, and Shopify data. The notebooks document the initial data exploration, mapping decisions, image normalization, and export process.

### D&J

The D&J adapter reads an Excel product export and maps product details, variants (color and size), prices, images, and suggested collections to Shopify fields.

The D&J implementation includes:

- Supplier-specific Excel parsing and lifecycle rules
- Shopify product and variant mapping
- Price conversion from the supplier's recommended ex-VAT price to the proposed VAT-inclusive Shopify price
- Change detection and local snapshot reports
- Live Shopify comparison and guarded creation of new draft products
- Collection-assignment utilities for the original catalog setup

**Current development:** Improving the association of product images with color variants, and reviewing sale pricing and stock data. These workflows are not yet presented as fully automated, production-ready features.

## Repository structure

```text
notebooks/                         # Snickers exploration and transformation
src/ecommerce_product_importer/
  models/                          # Catalog and product models
  readers/                         # Supplier-file readers
  services/                        # Validation, lifecycle, Shopify planning and sync
scripts/                           # CLI entry points and catalog maintenance tools
tests/                             # Unit tests and mocked Shopify API behavior
data/                               # Local supplier data, ignored by Git
.github/workflows/ci.yml           # Lint and tests on GitHub Actions
```

The source of truth for reusable application logic is `src/`. The `scripts/` files are command-line entry points rather than separate copies of the business logic.

## D&J workflow

Set up Python 3.12+ and [uv](https://docs.astral.sh/uv/), then install the environment:

```bash
uv sync
```

Use a local D&J `.xlsx` export (not committed to this repository).

**1. Preview the supplier mapping without changing Shopify:**

```bash
uv run python scripts/dj_shopify_preview.py path/to/dj-export.xlsx
```

**2. Compare with the live Shopify catalog (read-only):**

```bash
uv run python scripts/dj_shopify_live_dry_run.py path/to/dj-export.xlsx
```

**3. Plan a small batch of new products (dry-run by default):**

```bash
uv run python scripts/dj_shopify_apply_batch.py path/to/dj-export.xlsx --limit 5
```

Creating products requires both `--apply` and the exact confirmation value documented in `scripts/dj_shopify_apply_batch.py`. That script is designed to create **new D&J products as DRAFT**, not to update or publish existing ones. Always review its output before using the write mode.

For supplier change monitoring, `scripts/dj_refresh.py` creates local status snapshots and review reports.

**Collection setup:** `dj_collections_plan.py`, `dj_shopify_collections_preview.py`, and `dj_shopify_collections_apply.py` were built for the original D&J catalog setup. The Shopify collection utilities enforce specific checks, including an all-DRAFT expectation. They are **not general-purpose commands for an already published catalog** and must not be reused without updating and revalidating those conditions.

## Safety and data handling

- External writes require explicit action; previews and comparisons are read-only.
- Product creation uses DRAFT status, with no automatic publish or delete action.
- Shopify API credentials come from environment variables, never source code.
- Supplier exports, generated reports, credentials, and local data are excluded from version control by `.gitignore`.
- The repository contains transformation rules and mocked tests, not a live dump of supplier prices or Shopify data.

Typical Shopify environment variables:

```text
SHOPIFY_SHOP
SHOPIFY_CLIENT_ID
SHOPIFY_CLIENT_SECRET
```

## Tests and CI

```bash
uv run pytest -q
uv run ruff check .
```

The tests cover supplier parsing, lifecycle rules, catalog mapping, price calculations, planning, dry-run safeguards, and simulated Shopify mutations. GitHub Actions runs linting and tests on pushes and pull requests to `main`.

## Tech stack

Python, Pandas, openpyxl, XML tooling, Pillow, Shopify Admin GraphQL API, Requests, pytest, Ruff, uv, Jupyter and GitHub Actions.

## Purpose

A portfolio project demonstrating practical data engineering and MLOps-adjacent software practices: reproducible data transformations, separation of concerns, automated validation and testing, API integration, and carefully controlled changes to an external production system.
