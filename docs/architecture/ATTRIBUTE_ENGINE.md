# Catalog Attribute Engine

**Status:** Shipped (STEP 10)  
**Date:** 2026-08-07

## Purpose

Keep `Product` lean (sku, barcode, prices, unit, stock flags). Industry-specific fields use EAV — not columns on `Product`.

Do **not** store batch expiry, serials, or money integrity in attributes.

## Models

| Model | Role |
|-------|------|
| `AttributeDefinition` | Schema: code, data_type, flags; `tenant` null = system |
| `AttributeOption` | Select / multi-select choices |
| `BusinessTypeAttribute` | Assign definition to a business type |
| `CategoryAttribute` | Assign definition to a category |
| `ProductAttributeValue` | Typed value row per product × definition |

## Types

`text`, `int`, `decimal`, `bool`, `date`, `datetime`, `select`, `multi_select`

Flags: `is_required`, `is_searchable`, `is_filterable`, `is_pos_visible`, `is_reportable`

## APIs

- `GET/POST /api/v1/products/attributes/`
- `GET/PUT/DELETE /api/v1/products/attributes/:id/`
- `GET /api/v1/products/attributes/applicable/?category_id=`
- `PUT /api/v1/products/categories/:id/attributes/` — assign definition
- Product create/update: `attributes: [{ definition_id|code, value }, …]` or `{ code: value }`
- Product detail includes `attributes` array

## Seed

System defs `strength` (text) and `dosage_form` (select) assigned to business type `pharmacy` when present.

## FE

Product form loads applicable attributes for the selected category (+ tenant business type) and posts values with create/update.
