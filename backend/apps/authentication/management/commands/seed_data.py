from django.core.management.base import BaseCommand

from apps.authentication.models import Permission, Role, RolePermission, User
from apps.settings_app.models import Branch, Company

PERMISSIONS = [
    ("dashboard.view", "View Dashboard", "dashboard"),
    ("pos.access", "Access POS", "pos"),
    ("products.view", "View Products", "products"),
    ("products.create", "Create Products", "products"),
    ("products.update", "Update Products", "products"),
    ("products.delete", "Delete Products", "products"),
    ("inventory.view", "View Inventory", "inventory"),
    ("inventory.adjust", "Adjust Inventory", "inventory"),
    ("inventory.transfer", "Transfer Inventory", "inventory"),
    ("purchases.view", "View Purchases", "purchases"),
    ("purchases.create", "Create Purchases", "purchases"),
    ("sales.view", "View Sales", "sales"),
    ("sales.create", "Create Sales", "sales"),
    ("customers.view", "View Customers", "customers"),
    ("customers.create", "Create Customers", "customers"),
    ("customers.update", "Update Customers", "customers"),
    ("suppliers.view", "View Suppliers", "suppliers"),
    ("suppliers.create", "Create Suppliers", "suppliers"),
    ("suppliers.update", "Update Suppliers", "suppliers"),
    ("purchases.update", "Update Purchases", "purchases"),
    ("finance.view", "View Finance", "finance"),
    ("finance.create", "Create Finance Entries", "finance"),
    ("reports.view", "View Reports", "reports"),
    ("reports.export", "Export Reports", "reports"),
    ("users.view", "View Users", "users"),
    ("users.create", "Create Users", "users"),
    ("users.update", "Update Users", "users"),
    ("users.delete", "Delete Users", "users"),
    ("roles.view", "View Roles", "roles"),
    ("roles.create", "Create Roles", "roles"),
    ("roles.update", "Update Roles", "roles"),
    ("roles.delete", "Delete Roles", "roles"),
    ("branches.view", "View Branches", "branches"),
    ("branches.create", "Create Branches", "branches"),
    ("branches.update", "Update Branches", "branches"),
    ("branches.delete", "Delete Branches", "branches"),
    ("settings.view", "View Settings", "settings"),
    ("settings.update", "Update Settings", "settings"),
    ("settings.backup", "Manage Backups", "settings"),
    ("audit.view", "View Audit Logs", "audit"),
]

ROLE_PERMISSIONS = {
    "super_admin": "*",
    "admin": [
        "dashboard.view", "pos.access", "products.view", "products.create",
        "products.update", "products.delete", "inventory.view", "inventory.adjust",
        "inventory.transfer", "purchases.view", "purchases.create", "sales.view",
        "sales.create", "customers.view", "customers.create", "customers.update",
        "suppliers.view", "suppliers.create", "suppliers.update", "finance.view", "finance.create", "reports.view",
        "reports.export", "users.view", "users.create", "users.update",
        "roles.view", "branches.view", "branches.create", "branches.update",
        "settings.view", "settings.update", "audit.view",
    ],
    "branch_manager": [
        "dashboard.view", "pos.access", "products.view", "products.create",
        "products.update", "inventory.view", "inventory.adjust", "inventory.transfer",
        "purchases.view", "purchases.create", "purchases.update", "sales.view", "sales.create",
        "customers.view", "customers.create", "suppliers.view", "reports.view",
        "users.view", "branches.view", "settings.view",
    ],
    "accountant": [
        "dashboard.view", "finance.view", "finance.create", "reports.view",
        "reports.export", "sales.view", "purchases.view",
    ],
    "inventory_manager": [
        "dashboard.view", "products.view", "products.create", "products.update",
        "inventory.view", "inventory.adjust", "inventory.transfer",
        "purchases.view", "purchases.create", "suppliers.view", "reports.view",
    ],
    "cashier": ["pos.access"],
    "sales_staff": [
        "dashboard.view", "pos.access", "sales.view", "sales.create",
        "customers.view", "customers.create", "products.view",
    ],
    "read_only": [
        "dashboard.view", "products.view", "inventory.view", "sales.view",
        "customers.view", "suppliers.view", "finance.view", "reports.view",
    ],
}


class Command(BaseCommand):
    help = "Seed default roles, permissions, company, branch, and admin user"

    def handle(self, *args, **options):
        self.stdout.write("Seeding permissions...")
        perm_map = {}
        for codename, name, module in PERMISSIONS:
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={"name": name, "module": module},
            )
            perm_map[codename] = perm

        self.stdout.write("Seeding roles...")
        for slug, name in Role.SYSTEM_ROLES:
            role, _ = Role.objects.get_or_create(
                slug=slug,
                defaults={"name": name, "is_system": True},
            )
            RolePermission.objects.filter(role=role).delete()
            codes = ROLE_PERMISSIONS.get(slug, [])
            if codes == "*":
                codes = list(perm_map.keys())
            for code in codes:
                if code in perm_map:
                    RolePermission.objects.get_or_create(
                        role=role, permission=perm_map[code]
                    )

        self.stdout.write("Seeding company and branch...")
        company, _ = Company.objects.get_or_create(
            name="MDA Retail",
            defaults={"legal_name": "MDA Retail Ltd", "email": "info@mda.com"},
        )
        branch, _ = Branch.objects.get_or_create(
            company=company,
            code="BR01",
            defaults={"name": "Main Branch", "is_default": True, "is_active": True},
        )

        self.stdout.write("Seeding admin user...")
        admin_role = Role.objects.get(slug="super_admin")
        user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "admin@mda.com",
                "role": admin_role,
                "branch": branch,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        if created:
            user.set_password("admin12345")
            user.save()
            self.stdout.write(self.style.SUCCESS("Admin user created: admin / admin12345"))
        else:
            self.stdout.write("Admin user already exists.")

        self._seed_phase2(branch, user)
        self._seed_phase3(branch, user)
        self._seed_phase4(branch, user)

        self.stdout.write(self.style.SUCCESS("Seed completed."))

    def _seed_phase2(self, branch, user):
        from decimal import Decimal

        from apps.inventory.models import Warehouse
        from apps.inventory.services.inventory_service import InventoryService
        from apps.products.models import Brand, Category, Product, Unit

        self.stdout.write("Seeding Phase 2 catalog data...")

        units = [
            ("Piece", "pc"), ("Kilogram", "kg"), ("Liter", "L"), ("Box", "box"), ("Pack", "pk"),
        ]
        unit_map = {}
        for name, abbr in units:
            u, _ = Unit.objects.get_or_create(name=name, defaults={"abbreviation": abbr})
            unit_map[name] = u

        categories = ["Electronics", "Groceries", "Office Supplies", "Pharmacy", "Clothing"]
        cat_map = {}
        for name in categories:
            c, _ = Category.objects.get_or_create(name=name, defaults={"is_active": True})
            cat_map[name] = c

        brands = ["Generic", "TechPro", "FreshFarm", "OfficeMax"]
        brand_map = {}
        for name in brands:
            b, _ = Brand.objects.get_or_create(name=name, defaults={"is_active": True})
            brand_map[name] = b

        warehouse, _ = Warehouse.objects.get_or_create(
            branch=branch, code="WH01",
            defaults={"name": "Main Warehouse", "is_default": True, "is_active": True, "created_by": user},
        )

        sample_products = [
            ("SKU-1001", "6901234567890", "Wireless Earbuds Pro", "Electronics", "TechPro", "Piece", 25, 49.99, 79.99, 5, 120),
            ("SKU-1002", "6901234567891", "Organic Coffee Beans 1kg", "Groceries", "FreshFarm", "Kilogram", 8, 12.50, 19.99, 10, 45),
            ("SKU-1003", "6901234567892", "Smart Watch Series X", "Electronics", "TechPro", "Piece", 15, 89.00, 149.99, 5, 3),
            ("SKU-1004", "6901234567893", "A4 Notebook Pack", "Office Supplies", "OfficeMax", "Pack", 3, 4.00, 7.99, 15, 2),
            ("SKU-1005", "6901234567894", "USB-C Hub 7-in-1", "Electronics", "TechPro", "Piece", 12, 18.00, 34.99, 8, 0),
            ("SKU-1006", "6901234567895", "Premium Olive Oil 500ml", "Groceries", "FreshFarm", "Liter", 6, 7.50, 12.99, 10, 85),
            ("SKU-1007", "6901234567896", "HDMI Cable 2m", "Electronics", "Generic", "Piece", 4, 3.00, 8.99, 10, 0),
            ("SKU-1008", "6901234567897", "Ballpoint Pen Box", "Office Supplies", "OfficeMax", "Box", 2, 5.00, 9.99, 20, 150),
        ]

        for sku, barcode, name, cat, brand, unit, min_stock, cost, sell, _qty, qty in sample_products:
            image = f"https://picsum.photos/seed/{sku}/400/400"
            product, created = Product.objects.get_or_create(
                sku=sku,
                defaults={
                    "barcode": barcode,
                    "name": name,
                    "category": cat_map[cat],
                    "brand": brand_map[brand],
                    "unit": unit_map[unit],
                    "minimum_stock": min_stock,
                    "cost_price": Decimal(str(cost)),
                    "selling_price": Decimal(str(sell)),
                    "image": image,
                    "is_active": True,
                    "created_by": user,
                },
            )
            if not created:
                product.image = image
                product.save(update_fields=["image", "updated_at"])
            inv = InventoryService.ensure_inventory_record(product=product, warehouse=warehouse, user=user)
            if created or inv.quantity == 0:
                inv.quantity = qty
                inv.save(update_fields=["quantity", "updated_at"])

        self.stdout.write(self.style.SUCCESS("Phase 2 sample data seeded."))

    def _seed_phase3(self, branch, user):
        from decimal import Decimal

        from apps.customers.models import Customer
        from apps.purchases.models import PurchaseOrder
        from apps.purchases.services.purchase_service import PurchaseOrderService
        from apps.products.models import Product
        from apps.suppliers.models import Supplier

        self.stdout.write("Seeding Phase 3 partners data...")

        suppliers_data = [
            ("TechPro Distribution", "John Smith", "john@techpro.com", "+1-555-0101"),
            ("FreshFarm Wholesale", "Maria Garcia", "maria@freshfarm.com", "+1-555-0102"),
            ("OfficeMax Supply Co", "David Lee", "david@officemax.com", "+1-555-0103"),
        ]
        supplier_map = {}
        for idx, (name, contact, email, phone) in enumerate(suppliers_data, start=1):
            s, _ = Supplier.objects.get_or_create(
                supplier_code=f"SUP-{idx:05d}",
                defaults={
                    "company_name": name,
                    "contact_person": contact,
                    "email": email,
                    "phone": phone,
                    "payment_terms": 30,
                    "is_active": True,
                    "created_by": user,
                },
            )
            supplier_map[name] = s

        customers_data = [
            ("Alice Johnson", "alice@email.com", "+1-555-0201", "retail"),
            ("Metro Retail Chain", "orders@metro.com", "+1-555-0202", "wholesale"),
            ("Acme Corp", "procurement@acme.com", "+1-555-0203", "corporate"),
        ]
        for idx, (name, email, phone, ctype) in enumerate(customers_data, start=1):
            Customer.objects.get_or_create(
                customer_code=f"CUST-{idx:05d}",
                defaults={
                    "full_name": name,
                    "email": email,
                    "phone": phone,
                    "customer_type": ctype,
                    "credit_limit": Decimal("5000") if ctype != "retail" else Decimal("500"),
                    "branch": branch,
                    "is_active": True,
                    "created_by": user,
                },
            )

        if not PurchaseOrder.active_objects().exists():
            product = Product.active_objects().first()
            supplier = supplier_map["TechPro Distribution"]
            if product:
                PurchaseOrderService.create(
                    data={
                        "supplier_id": str(supplier.id),
                        "branch_id": str(branch.id),
                        "status": PurchaseOrder.STATUS_ORDERED,
                        "notes": "Sample purchase order",
                    },
                    items=[{
                        "product_id": str(product.id),
                        "quantity_ordered": Decimal("50"),
                        "unit_cost": product.cost_price,
                    }],
                    user=user,
                )

        self.stdout.write(self.style.SUCCESS("Phase 3 sample data seeded."))

    def _seed_phase4(self, branch, user):
        from datetime import timedelta
        from decimal import Decimal

        from django.utils import timezone

        from apps.customers.models import Customer
        from apps.inventory.models import Warehouse
        from apps.products.models import Product
        from apps.purchases.models import PurchaseOrder
        from apps.purchases.services.purchase_service import PurchaseOrderService
        from apps.sales.models import Invoice, Quotation
        from apps.sales.services.sales_service import InvoiceService, QuotationService
        from apps.settings_app.models import Branch, Company
        from apps.suppliers.models import Supplier

        self.stdout.write("Seeding Phase 4 sales & extended data...")

        company = Company.active_objects().first()
        branch2, _ = Branch.objects.get_or_create(
            company=company,
            code="BR02",
            defaults={
                "name": "Downtown Branch",
                "address": "456 Commerce Ave",
                "phone": "+1-555-0300",
                "is_active": True,
                "created_by": user,
            },
        )

        Warehouse.objects.get_or_create(
            branch=branch2,
            code="WH02",
            defaults={"name": "Downtown Warehouse", "is_active": True, "created_by": user},
        )

        customers = list(Customer.active_objects().all()[:3])
        products = list(Product.active_objects().all()[:4])
        suppliers = list(Supplier.active_objects().all())

        if suppliers and products and not PurchaseOrder.active_objects().filter(status=PurchaseOrder.STATUS_DRAFT).exists():
            PurchaseOrderService.create(
                data={
                    "supplier_id": str(suppliers[0].id),
                    "branch_id": str(branch.id),
                    "status": PurchaseOrder.STATUS_DRAFT,
                    "notes": "Draft PO for office restock",
                },
                items=[{
                    "product_id": str(products[1].id),
                    "quantity_ordered": Decimal("25"),
                    "unit_cost": products[1].cost_price,
                }],
                user=user,
            )

        if suppliers and products and PurchaseOrder.active_objects().count() < 3:
            PurchaseOrderService.create(
                data={
                    "supplier_id": str(suppliers[1].id if len(suppliers) > 1 else suppliers[0].id),
                    "branch_id": str(branch.id),
                    "status": PurchaseOrder.STATUS_RECEIVED,
                    "notes": "Received shipment",
                },
                items=[{
                    "product_id": str(products[2].id),
                    "quantity_ordered": Decimal("100"),
                    "unit_cost": products[2].cost_price,
                }],
                user=user,
            )

        if customers and products and not Quotation.active_objects().exists():
            QuotationService.create(
                data={
                    "customer_id": str(customers[0].id),
                    "branch_id": str(branch.id),
                    "status": Quotation.STATUS_SENT,
                    "valid_until": (timezone.localdate() + timedelta(days=14)).isoformat(),
                    "notes": "Bulk order quote for retail customer",
                },
                items=[
                    {"product_id": str(products[0].id), "quantity": Decimal("10"), "unit_price": products[0].selling_price},
                    {"product_id": str(products[1].id), "quantity": Decimal("5"), "unit_price": products[1].selling_price},
                ],
                user=user,
            )
            QuotationService.create(
                data={
                    "customer_id": str(customers[1].id if len(customers) > 1 else customers[0].id),
                    "branch_id": str(branch.id),
                    "status": Quotation.STATUS_DRAFT,
                    "valid_until": (timezone.localdate() + timedelta(days=30)).isoformat(),
                    "notes": "Wholesale pricing proposal",
                },
                items=[
                    {"product_id": str(products[2].id), "quantity": Decimal("50"), "unit_price": products[2].selling_price},
                ],
                user=user,
            )

        if customers and products and not Invoice.active_objects().exists():
            today = timezone.localdate()
            InvoiceService.create(
                data={
                    "customer_id": str(customers[0].id),
                    "branch_id": str(branch.id),
                    "status": Invoice.STATUS_PAID,
                    "issue_date": today.isoformat(),
                    "due_date": (today + timedelta(days=30)).isoformat(),
                    "amount_paid": Decimal("0"),
                    "notes": "Paid invoice - walk-in sale",
                },
                items=[
                    {"product_id": str(products[0].id), "quantity": Decimal("2"), "unit_price": products[0].selling_price},
                ],
                user=user,
            )
            inv = InvoiceService.create(
                data={
                    "customer_id": str(customers[2].id if len(customers) > 2 else customers[0].id),
                    "branch_id": str(branch.id),
                    "status": Invoice.STATUS_SENT,
                    "issue_date": today.isoformat(),
                    "due_date": (today + timedelta(days=15)).isoformat(),
                    "notes": "Corporate account invoice",
                },
                items=[
                    {"product_id": str(products[3].id), "quantity": Decimal("20"), "unit_price": products[3].selling_price},
                    {"product_id": str(products[1].id), "quantity": Decimal("10"), "unit_price": products[1].selling_price},
                ],
                user=user,
            )
            inv.amount_paid = Decimal("0")
            inv.save(update_fields=["amount_paid"])
            InvoiceService.create(
                data={
                    "customer_id": str(customers[1].id if len(customers) > 1 else customers[0].id),
                    "branch_id": str(branch.id),
                    "status": Invoice.STATUS_DRAFT,
                    "issue_date": today.isoformat(),
                    "notes": "Draft invoice pending approval",
                },
                items=[
                    {"product_id": str(products[2].id), "quantity": Decimal("3"), "unit_price": products[2].selling_price},
                ],
                user=user,
            )

        # Mark one invoice as paid with amount
        paid = Invoice.active_objects().filter(status=Invoice.STATUS_PAID).first()
        if paid:
            paid.amount_paid = paid.total_amount
            paid.save(update_fields=["amount_paid", "updated_at"])

        self.stdout.write(self.style.SUCCESS("Phase 4 sales data seeded."))

