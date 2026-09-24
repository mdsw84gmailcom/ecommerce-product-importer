# Ecommerce Product Importer

A reusable data pipeline for transforming supplier product data into a structured Shopify-ready catalog and safely synchronizing product changes with Shopify.

The project was originally built to handle a large Snickers Workwear product catalog, but the pipeline is designed so that the same workflow can be reused for future supplier updates.

## Project Overview

Supplier data arrives from multiple sources and formats:

- Excel price lists
- XML product feeds
- Product images
- Existing Shopify catalog data

The pipeline combines and validates these sources before creating a normalized Shopify export.

```text
Supplier price list + product feed
                ↓
        Data transformation
                ↓
      Product validation
                ↓
       Image normalization
                ↓
        Shopify export
                ↓
      Shopify comparison
                ↓
          Change plan
                ↓
     Dry-run / synchronization
```

The synchronization layer compares the generated catalog with the existing Shopify store before any changes are applied.

Products and variants can be classified as:

- `NEW`
- `UPDATED`
- `UNCHANGED`
- `DISCONTINUED`

This makes it possible to review changes before updating the live store.

## Current Dataset

The current Snickers pipeline processes:

- 13,741 valid product variants
- 513 Shopify products
- 1,284 normalized product images

The latest synchronization comparison found all 13,741 variants unchanged and identified 10 product-level description updates.

## Project Structure

```text
notebooks/
├── 01_price_list_analysis.ipynb
├── 02_product_feed_analysis.ipynb
├── 03_abicart_analysis.ipynb
├── 04_mapping_strategy.ipynb
├── 05_data_transformation.ipynb
├── 06_normalize_product_images.ipynb
└── 07_shopify_export.ipynb

src/ecommerce_product_importer/
├── models/
├── readers/
└── services/
    ├── merge_engine.py
    └── shopify_sync.py

tests/
├── test_merge_engine.py
├── test_product_feed_reader.py
└── test_shopify_sync.py
```

## Pipeline

### 1. Data Transformation

`05_data_transformation.ipynb`

Combines the supplier price list and XML product feed into a normalized product dataset.

The transformation includes:

- price normalization
- product and variant mapping
- SKU validation
- required-field validation
- supplier-specific exclusions
- image URL extraction
- data-quality reporting

### 2. Image Normalization

`06_normalize_product_images.ipynb`

Downloads and normalizes supplier product images for consistent ecommerce presentation.

The image pipeline includes:

- retry handling
- image trimming
- resizing
- centering
- consistent canvas dimensions
- normalized image metadata

### 3. Shopify Export

`07_shopify_export.ipynb`

Transforms the normalized catalog into Shopify-compatible product and variant data.

The export contains Shopify handles, product descriptions, options, SKUs, prices and barcodes.

### 4. Shopify Synchronization

`shopify_sync.py`

The synchronization service retrieves the existing Shopify catalog through the Shopify Admin GraphQL API and compares it with the newly generated catalog.

The comparison is performed before mutations are allowed.

The synchronization workflow supports:

```text
NEW
UPDATED
UNCHANGED
DISCONTINUED
```

Product updates are converted into explicit mutation payloads before execution.

## Safe Shopify Updates

Safety is intentionally built into the synchronization workflow.

Shopify mutations use:

```python
dry_run=True
```

by default.

A dry-run generates the same update plan and payloads without modifying the Shopify store.

The mutation path is also tested with mocked HTTP requests so that write behavior can be verified without sending changes to Shopify.

Credentials are loaded from environment variables and are not stored in the repository.

Required environment variables:

```text
SHOPIFY_SHOP
SHOPIFY_CLIENT_ID
SHOPIFY_CLIENT_SECRET
```

## Testing

Run the test suite with:

```bash
uv run pytest
```

The test suite covers data merging, product feed handling, Shopify comparisons, change planning, payload generation, dry-run behavior and mocked Shopify mutations.

## Tech Stack

- Python
- Pandas
- Jupyter
- Shopify Admin GraphQL API
- Requests
- Pillow
- pytest
- uv
- python-dotenv

## Purpose

The project demonstrates a practical ecommerce data-engineering workflow with a focus on reusable transformations, data validation, API integration, automated testing and safe synchronization with an external production system.

It was developed as a portfolio project while studying MLOps Engineering.