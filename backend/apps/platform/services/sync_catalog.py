"""Serialize and apply catalog + transactional data for shop ↔ cloud sync."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.customers.models import Customer
from apps.inventory.models import Inventory, Warehouse
from apps.platform.models import Tenant
from apps.products.models import Brand, Category, Product, Unit
from apps.sales.models import Invoice, InvoiceItem
from apps.settings_app.models import Branch, Company
from apps.settings_app.services.settings_service import SettingsService


def parse_since(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if timezone.is_naive(dt):
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    except ValueError:
        return None


def _iso(dt) -> str:
    return dt.isoformat() if dt else ""


def _is_newer(remote_updated: str, local_updated) -> bool:
    remote = parse_since(remote_updated)
    if not remote or not local_updated:
        return False
    return local_updated > remote


class CatalogSyncEngine:
  @staticmethod
  def _company_for_tenant(tenant: Tenant) -> Company | None:
      return Company.active_objects().filter(tenant=tenant).first()

  @staticmethod
  def _local_company() -> Company | None:
      return Company.active_objects().first()

  @staticmethod
  def _default_branch(company: Company | None) -> Branch | None:
      if not company:
          return None
      return Branch.active_objects().filter(company=company, is_active=True).first()

  @staticmethod
  def _default_warehouse(company: Company | None) -> Warehouse | None:
      branch = CatalogSyncEngine._default_branch(company)
      if not branch:
          return None
      wh = Warehouse.active_objects().filter(branch=branch, is_default=True).first()
      return wh or Warehouse.active_objects().filter(branch=branch).first()

  @staticmethod
  def _filter_since(qs, since: datetime | None):
      if since:
          return qs.filter(updated_at__gte=since)
      return qs

  @staticmethod
  def export_pull_bundle(*, tenant: Tenant, since: datetime | None = None) -> dict:
      company = CatalogSyncEngine._company_for_tenant(tenant)
      warehouse = CatalogSyncEngine._default_warehouse(company)

      units = CatalogSyncEngine._filter_since(Unit.active_objects(), since)
      brands = CatalogSyncEngine._filter_since(Brand.active_objects(), since)
      categories = CatalogSyncEngine._filter_since(
          Category.active_objects().select_related("parent"), since
      )
      products = CatalogSyncEngine._filter_since(
          Product.active_objects().select_related("category", "brand", "unit"), since
      )

      inv_by_product: dict[str, Decimal] = {}
      if warehouse:
          for row in Inventory.active_objects().filter(warehouse=warehouse).select_related("product"):
              inv_by_product[str(row.product_id)] = row.quantity

      subscription = None
      sub = getattr(tenant, "subscription", None)
      if sub:
          subscription = sub.alert_payload()

      customers_qs = Customer.active_objects().select_related("branch")
      customers_qs = CatalogSyncEngine._filter_since(customers_qs, since)

      return {
          "server_time": timezone.now().isoformat(),
          "since": _iso(since),
          "subscription": subscription,
          "units": [
              {
                  "name": u.name,
                  "abbreviation": u.abbreviation,
                  "is_active": u.is_active,
                  "updated_at": _iso(u.updated_at),
              }
              for u in units
          ],
          "brands": [
              {
                  "name": b.name,
                  "description": b.description,
                  "is_active": b.is_active,
                  "updated_at": _iso(b.updated_at),
              }
              for b in brands
          ],
          "categories": [
              {
                  "name": c.name,
                  "parent_name": c.parent.name if c.parent_id else "",
                  "description": c.description,
                  "is_active": c.is_active,
                  "updated_at": _iso(c.updated_at),
              }
              for c in categories
          ],
          "products": [
              {
                  "sku": p.sku,
                  "barcode": p.barcode or "",
                  "name": p.name,
                  "category_name": p.category.name,
                  "brand_name": p.brand.name if p.brand_id else "",
                  "unit_abbreviation": p.unit.abbreviation,
                  "cost_price": str(p.cost_price),
                  "selling_price": str(p.selling_price),
                  "minimum_stock": p.minimum_stock,
                  "description": p.description,
                  "image": p.image,
                  "is_active": p.is_active,
                  "quantity": float(inv_by_product.get(str(p.id), 0)),
                  "updated_at": _iso(p.updated_at),
              }
              for p in products
          ],
          "customers": [
              {
                  "customer_code": c.customer_code,
                  "full_name": c.full_name,
                  "email": c.email,
                  "phone": c.phone,
                  "address": c.address,
                  "customer_type": c.customer_type,
                  "credit_limit": str(c.credit_limit),
                  "is_active": c.is_active,
                  "updated_at": _iso(c.updated_at),
              }
              for c in customers_qs[:1000]
          ],
      }

  @staticmethod
  def export_shop_push(*, since: datetime | None = None) -> dict:
      company = CatalogSyncEngine._local_company()
      branch = CatalogSyncEngine._default_branch(company)
      warehouse = CatalogSyncEngine._default_warehouse(company)

      customers_qs = Customer.active_objects()
      customers_qs = CatalogSyncEngine._filter_since(customers_qs, since)

      inv_qs = Invoice.active_objects().select_related("customer", "branch").prefetch_related("items__product")
      inv_qs = CatalogSyncEngine._filter_since(inv_qs, since)

      inventory_rows = []
      if warehouse:
          for row in Inventory.active_objects().filter(warehouse=warehouse).select_related("product"):
              inventory_rows.append(
                  {
                      "sku": row.product.sku,
                      "quantity": float(row.quantity),
                      "updated_at": _iso(row.updated_at),
                  }
              )

      return {
          "customers": [
              {
                  "customer_code": c.customer_code,
                  "full_name": c.full_name,
                  "email": c.email,
                  "phone": c.phone,
                  "address": c.address,
                  "customer_type": c.customer_type,
                  "credit_limit": str(c.credit_limit),
                  "is_active": c.is_active,
                  "updated_at": _iso(c.updated_at),
              }
              for c in customers_qs[:1000]
          ],
          "invoices": [
              {
                  "invoice_number": inv.invoice_number,
                  "issue_date": inv.issue_date.isoformat(),
                  "status": inv.status,
                  "subtotal": float(inv.subtotal),
                  "discount_amount": float(inv.discount_amount),
                  "tax_amount": float(inv.tax_amount),
                  "total_amount": float(inv.total_amount),
                  "amount_paid": float(inv.amount_paid),
                  "customer_code": inv.customer.customer_code if inv.customer_id else "",
                  "customer_name": inv.customer.full_name if inv.customer_id else "",
                  "notes": inv.notes,
                  "updated_at": _iso(inv.updated_at),
                  "items": [
                      {
                          "sku": item.product.sku,
                          "quantity": float(item.quantity),
                          "unit_price": float(item.unit_price),
                          "line_total": float(item.line_total),
                      }
                      for item in inv.items.all()
                  ],
              }
              for inv in inv_qs[:500]
          ],
          "inventory": inventory_rows[:2000],
          "branch_code": branch.code if branch else "",
      }

  @staticmethod
  @transaction.atomic
  def apply_pull_bundle(data: dict, *, user=None) -> dict:
      stats = {"units": 0, "brands": 0, "categories": 0, "products": 0, "customers": 0, "inventory": 0}

      for row in data.get("units", []):
          if CatalogSyncEngine._upsert_unit(row):
              stats["units"] += 1

      for row in data.get("brands", []):
          if CatalogSyncEngine._upsert_brand(row):
              stats["brands"] += 1

      for row in data.get("categories", []):
          if not row.get("parent_name"):
              if CatalogSyncEngine._upsert_category(row, parent=None):
                  stats["categories"] += 1
      for row in data.get("categories", []):
          if row.get("parent_name"):
              parent = Category.active_objects().filter(name=row["parent_name"]).first()
              if CatalogSyncEngine._upsert_category(row, parent=parent):
                  stats["categories"] += 1

      for row in data.get("products", []):
          if CatalogSyncEngine._upsert_product(row):
              stats["products"] += 1

      for row in data.get("customers", []):
          if CatalogSyncEngine._upsert_customer(row, user=user):
              stats["customers"] += 1

      warehouse = CatalogSyncEngine._default_warehouse(CatalogSyncEngine._local_company())
      if warehouse:
          for row in data.get("products", []):
              if "quantity" in row and CatalogSyncEngine._upsert_inventory(row, warehouse, user):
                  stats["inventory"] += 1

      sub = data.get("subscription")
      if sub:
          SettingsService.upsert(
              key="sync.subscription_alert",
              value=json.dumps(sub),
              category="sync",
              user=user,
          )

      return stats

  @staticmethod
  @transaction.atomic
  def apply_shop_push(*, tenant: Tenant, payload: dict, user=None) -> dict:
      company = CatalogSyncEngine._company_for_tenant(tenant)
      branch = CatalogSyncEngine._default_branch(company)
      warehouse = CatalogSyncEngine._default_warehouse(company)
      stats = {"customers": 0, "invoices": 0, "inventory": 0}

      for row in payload.get("customers", []):
          if CatalogSyncEngine._upsert_customer(row, branch=branch, user=user):
              stats["customers"] += 1

      if warehouse:
          for row in payload.get("inventory", []):
              if CatalogSyncEngine._upsert_inventory(row, warehouse, user):
                  stats["inventory"] += 1

      if branch:
          for row in payload.get("invoices", []):
              if CatalogSyncEngine._upsert_invoice(row, branch=branch, user=user):
                  stats["invoices"] += 1

      return stats

  @staticmethod
  def _upsert_unit(row: dict) -> bool:
      abbr = row.get("abbreviation", "").strip()
      if not abbr:
          return False
      existing = Unit.active_objects().filter(abbreviation=abbr).first()
      if existing and _is_newer(row.get("updated_at", ""), existing.updated_at):
          return False
      Unit.objects.update_or_create(
          abbreviation=abbr,
          defaults={
              "name": row.get("name", abbr),
              "is_active": row.get("is_active", True),
              "deleted_at": None,
          },
      )
      return True

  @staticmethod
  def _upsert_brand(row: dict) -> bool:
      name = row.get("name", "").strip()
      if not name:
          return False
      existing = Brand.active_objects().filter(name=name).first()
      if existing and _is_newer(row.get("updated_at", ""), existing.updated_at):
          return False
      Brand.objects.update_or_create(
          name=name,
          defaults={
              "description": row.get("description", ""),
              "is_active": row.get("is_active", True),
              "deleted_at": None,
          },
      )
      return True

  @staticmethod
  def _upsert_category(row: dict, parent: Category | None) -> bool:
      name = row.get("name", "").strip()
      if not name:
          return False
      existing = Category.active_objects().filter(name=name).first()
      if existing and _is_newer(row.get("updated_at", ""), existing.updated_at):
          return False
      Category.objects.update_or_create(
          name=name,
          defaults={
              "parent": parent,
              "description": row.get("description", ""),
              "is_active": row.get("is_active", True),
              "deleted_at": None,
          },
      )
      return True

  @staticmethod
  def _upsert_product(row: dict) -> bool:
      sku = row.get("sku", "").strip()
      if not sku:
          return False
      existing = Product.active_objects().filter(sku=sku).first()
      if existing and _is_newer(row.get("updated_at", ""), existing.updated_at):
          return False

      category = Category.active_objects().filter(name=row.get("category_name", "")).first()
      if not category:
          category, _ = Category.objects.get_or_create(
              name=row.get("category_name") or "General",
              defaults={"is_active": True},
          )

      unit = Unit.active_objects().filter(abbreviation=row.get("unit_abbreviation", "")).first()
      if not unit:
          abbr = row.get("unit_abbreviation") or "ea"
          unit, _ = Unit.objects.get_or_create(
              abbreviation=abbr,
              defaults={"name": abbr.title(), "is_active": True},
          )

      brand = None
      brand_name = (row.get("brand_name") or "").strip()
      if brand_name:
          brand, _ = Brand.objects.get_or_create(name=brand_name, defaults={"is_active": True})

      barcode = row.get("barcode") or None
      defaults = {
          "name": row.get("name", sku),
          "category": category,
          "brand": brand,
          "unit": unit,
          "cost_price": Decimal(str(row.get("cost_price", 0))),
          "selling_price": Decimal(str(row.get("selling_price", 0))),
          "minimum_stock": int(row.get("minimum_stock", 5)),
          "description": row.get("description", ""),
          "image": row.get("image", ""),
          "is_active": row.get("is_active", True),
          "deleted_at": None,
      }
      if barcode:
          defaults["barcode"] = barcode

      Product.objects.update_or_create(sku=sku, defaults=defaults)
      return True

  @staticmethod
  def _upsert_customer(row: dict, *, branch: Branch | None = None, user=None) -> bool:
      code = row.get("customer_code", "").strip()
      if not code:
          return False
      existing = Customer.active_objects().filter(customer_code=code).first()
      if existing and _is_newer(row.get("updated_at", ""), existing.updated_at):
          return False
      if branch is None:
          branch = CatalogSyncEngine._default_branch(CatalogSyncEngine._local_company())
      Customer.objects.update_or_create(
          customer_code=code,
          defaults={
              "full_name": row.get("full_name", code),
              "email": row.get("email", ""),
              "phone": row.get("phone", ""),
              "address": row.get("address", ""),
              "customer_type": row.get("customer_type", "retail"),
              "credit_limit": Decimal(str(row.get("credit_limit", 0))),
              "is_active": row.get("is_active", True),
              "branch": branch,
              "deleted_at": None,
              "updated_by": user,
          },
      )
      return True

  @staticmethod
  def _upsert_inventory(row: dict, warehouse: Warehouse, user=None) -> bool:
      sku = row.get("sku", "").strip()
      if not sku:
          return False
      product = Product.active_objects().filter(sku=sku).first()
      if not product:
          return False
      inv = Inventory.active_objects().filter(product=product, warehouse=warehouse).first()
      if inv and _is_newer(row.get("updated_at", ""), inv.updated_at):
          return False
      qty = Decimal(str(row.get("quantity", 0)))
      Inventory.objects.update_or_create(
          product=product,
          warehouse=warehouse,
          defaults={"quantity": qty, "updated_by": user, "deleted_at": None},
      )
      return True

  @staticmethod
  def _upsert_invoice(row: dict, *, branch: Branch, user=None) -> bool:
      number = row.get("invoice_number", "").strip()
      if not number:
          return False
      existing = Invoice.active_objects().filter(branch=branch, invoice_number=number).first()
      if existing and _is_newer(row.get("updated_at", ""), existing.updated_at):
          return False

      customer_code = row.get("customer_code", "").strip()
      customer = None
      if customer_code:
          customer = Customer.active_objects().filter(customer_code=customer_code).first()
      if not customer:
          name = row.get("customer_name") or "Walk-in Customer"
          customer = Customer.active_objects().filter(full_name__iexact=name).first()
      if not customer:
          customer = Customer.objects.create(
              customer_code=customer_code or f"SYNC-{number}",
              full_name=row.get("customer_name") or "Walk-in Customer",
              branch=branch,
              created_by=user,
          )

      issue_raw = row.get("issue_date") or timezone.localdate()
      if isinstance(issue_raw, str):
          issue_date = date.fromisoformat(issue_raw[:10])
      else:
          issue_date = issue_raw

      invoice, created = Invoice.objects.update_or_create(
          branch=branch,
          invoice_number=number,
          defaults={
              "customer": customer,
              "status": row.get("status", Invoice.STATUS_PAID),
              "issue_date": issue_date,
              "subtotal": Decimal(str(row.get("subtotal", 0))),
              "discount_amount": Decimal(str(row.get("discount_amount", 0))),
              "tax_amount": Decimal(str(row.get("tax_amount", 0))),
              "total_amount": Decimal(str(row.get("total_amount", 0))),
              "amount_paid": Decimal(str(row.get("amount_paid", 0))),
              "notes": row.get("notes", ""),
              "updated_by": user,
              "deleted_at": None,
          },
      )

      if created or row.get("items"):
          invoice.items.all().delete()
          for item in row.get("items", []):
              product = Product.active_objects().filter(sku=item.get("sku", "")).first()
              if not product:
                  continue
              InvoiceItem.objects.create(
                  invoice=invoice,
                  product=product,
                  quantity=Decimal(str(item.get("quantity", 0))),
                  unit_price=Decimal(str(item.get("unit_price", 0))),
                  line_total=Decimal(str(item.get("line_total", 0))),
                  created_by=user,
              )
      return True
