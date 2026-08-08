"""Backfill tenant_id on operational tables (STEP 06 Stage A1)."""

from __future__ import annotations


def _legacy_tenant(apps):
    Tenant = apps.get_model("platform", "Tenant")
    tenant, _ = Tenant.objects.get_or_create(
        slug="legacy-unassigned",
        defaults={
            "name": "Legacy Unassigned",
            "status": "suspended",
            "is_active": False,
            "timezone": "UTC",
            "currency": "USD",
            "language": "en",
        },
    )
    return tenant


def _primary_tenant_id(apps):
    Company = apps.get_model("settings_app", "Company")
    company = (
        Company.objects.filter(tenant_id__isnull=False, deleted_at__isnull=True)
        .order_by("created_at")
        .first()
    )
    if company:
        return company.tenant_id
    Tenant = apps.get_model("platform", "Tenant")
    tenant = (
        Tenant.objects.filter(deleted_at__isnull=True)
        .exclude(slug="legacy-unassigned")
        .order_by("created_at")
        .first()
    )
    return tenant.id if tenant else _legacy_tenant(apps).id


def backfill_tenant_isolation(apps, schema_editor):
    Company = apps.get_model("settings_app", "Company")
    Branch = apps.get_model("settings_app", "Branch")
    Setting = apps.get_model("settings_app", "Setting")
    Warehouse = apps.get_model("inventory", "Warehouse")
    Inventory = apps.get_model("inventory", "Inventory")
    StockMovement = apps.get_model("inventory", "StockMovement")
    InventoryTransaction = apps.get_model("inventory", "InventoryTransaction")
    InventoryAdjustment = apps.get_model("inventory", "InventoryAdjustment")
    Category = apps.get_model("products", "Category")
    Brand = apps.get_model("products", "Brand")
    Unit = apps.get_model("products", "Unit")
    Product = apps.get_model("products", "Product")
    Customer = apps.get_model("customers", "Customer")
    Supplier = apps.get_model("suppliers", "Supplier")
    Invoice = apps.get_model("sales", "Invoice")
    Quotation = apps.get_model("sales", "Quotation")
    Expense = apps.get_model("sales", "Expense")
    DocumentSequence = apps.get_model("sales", "DocumentSequence")
    PurchaseOrder = apps.get_model("purchases", "PurchaseOrder")
    AuditLog = apps.get_model("audit", "AuditLog")
    User = apps.get_model("authentication", "User")

    fallback_id = _primary_tenant_id(apps)
    legacy_id = _legacy_tenant(apps).id

    # Branches from company
    for branch in Branch.objects.filter(tenant_id__isnull=True).select_related("company"):
        tid = getattr(branch.company, "tenant_id", None) or fallback_id
        Branch.objects.filter(pk=branch.pk).update(tenant_id=tid)

    for setting in Setting.objects.filter(tenant_id__isnull=True).select_related("company", "branch"):
        tid = None
        if setting.company_id and setting.company.tenant_id:
            tid = setting.company.tenant_id
        elif setting.branch_id:
            tid = setting.branch.tenant_id or (
                setting.branch.company.tenant_id if setting.branch.company_id else None
            )
        Setting.objects.filter(pk=setting.pk).update(tenant_id=tid or fallback_id)

    for wh in Warehouse.objects.filter(tenant_id__isnull=True).select_related("branch"):
        tid = wh.branch.tenant_id if wh.branch_id else fallback_id
        Warehouse.objects.filter(pk=wh.pk).update(tenant_id=tid or fallback_id)

    # Catalog → primary tenant (desktop single-shop) or legacy if none
    catalog_tid = fallback_id or legacy_id
    Category.objects.filter(tenant_id__isnull=True).update(tenant_id=catalog_tid)
    Brand.objects.filter(tenant_id__isnull=True).update(tenant_id=catalog_tid)
    Unit.objects.filter(tenant_id__isnull=True).update(tenant_id=catalog_tid)
    Product.objects.filter(tenant_id__isnull=True).update(tenant_id=catalog_tid)
    Supplier.objects.filter(tenant_id__isnull=True).update(tenant_id=catalog_tid)

    for customer in Customer.objects.filter(tenant_id__isnull=True).select_related("branch"):
        tid = None
        if customer.branch_id:
            tid = customer.branch.tenant_id
        Customer.objects.filter(pk=customer.pk).update(tenant_id=tid or catalog_tid)

    def _branch_tenant(obj):
        if obj.branch_id and obj.branch.tenant_id:
            return obj.branch.tenant_id
        return catalog_tid

    for model in (Invoice, Quotation, Expense, DocumentSequence, PurchaseOrder, InventoryAdjustment):
        for row in model.objects.filter(tenant_id__isnull=True).select_related("branch"):
            model.objects.filter(pk=row.pk).update(tenant_id=_branch_tenant(row))

    for inv in Inventory.objects.filter(tenant_id__isnull=True).select_related("warehouse"):
        tid = inv.warehouse.tenant_id if inv.warehouse_id else catalog_tid
        Inventory.objects.filter(pk=inv.pk).update(tenant_id=tid or catalog_tid)

    for row in StockMovement.objects.filter(tenant_id__isnull=True).select_related("warehouse"):
        tid = row.warehouse.tenant_id if row.warehouse_id else catalog_tid
        StockMovement.objects.filter(pk=row.pk).update(tenant_id=tid or catalog_tid)

    for row in InventoryTransaction.objects.filter(tenant_id__isnull=True).select_related(
        "inventory__warehouse"
    ):
        tid = None
        if row.inventory_id and row.inventory.warehouse_id:
            tid = row.inventory.warehouse.tenant_id or row.inventory.tenant_id
        InventoryTransaction.objects.filter(pk=row.pk).update(tenant_id=tid or catalog_tid)

    # User.tenant exists from authentication.0003 — skip safely if historical model lacks it.
    user_field_names = {f.name for f in User._meta.get_fields()}
    if "tenant" in user_field_names:
        for user in User.objects.filter(tenant_id__isnull=True, deleted_at__isnull=True).select_related(
            "branch__company"
        ):
            tid = None
            if user.branch_id and user.branch.company_id:
                tid = user.branch.company.tenant_id or getattr(user.branch, "tenant_id", None)
            if tid:
                User.objects.filter(pk=user.pk).update(tenant_id=tid)

    for log in AuditLog.objects.filter(tenant_id__isnull=True).select_related("user"):
        tid = None
        if log.user_id and "tenant" in user_field_names:
            tid = getattr(log.user, "tenant_id", None)
        if tid:
            AuditLog.objects.filter(pk=log.pk).update(tenant_id=tid)


def noop_reverse(apps, schema_editor):
    pass
