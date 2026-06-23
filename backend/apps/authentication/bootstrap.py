"""System bootstrap: roles and permissions (no users, company, or demo data)."""

from apps.authentication.models import Permission, Role, RolePermission

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
    ("staff.performance.view", "View Staff Performance", "staff"),
    ("staff.performance.evaluate", "Evaluate Staff Performance", "staff"),
    ("platform.view", "View Platform Shops", "platform"),
    ("platform.manage", "Manage Platform Shops", "platform"),
    ("subscriptions.view", "View Subscriptions", "platform"),
    ("subscriptions.manage", "Manage Subscriptions", "platform"),
    ("futsal.view", "View Futsal Module", "futsal"),
    ("futsal.manage", "Manage Courts, Teams & Bookings", "futsal"),
    ("futsal.finance", "Manage Futsal Income & Expenses", "futsal"),
]

ROLE_PERMISSIONS = {
    "platform_admin": "*",
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
        "staff.performance.view", "staff.performance.evaluate",
        "futsal.view", "futsal.manage", "futsal.finance",
    ],
    "branch_manager": [
        "dashboard.view", "pos.access", "products.view", "products.create",
        "products.update", "inventory.view", "inventory.adjust", "inventory.transfer",
        "purchases.view", "purchases.create", "purchases.update", "sales.view", "sales.create",
        "customers.view", "customers.create", "suppliers.view", "reports.view",
        "users.view", "branches.view", "settings.view",
        "staff.performance.view", "staff.performance.evaluate",
        "futsal.view", "futsal.manage", "futsal.finance",
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
    "futsal_staff": [
        "dashboard.view", "futsal.view", "futsal.manage",
        "customers.view", "customers.create",
    ],
    "futsal_manager": [
        "dashboard.view", "futsal.view", "futsal.manage", "futsal.finance",
        "customers.view", "customers.create", "reports.view", "finance.view",
    ],
    "cafeteria_cashier": [
        "pos.access", "customers.view", "customers.create", "products.view",
    ],
    "shop_group_manager": [
        "dashboard.view", "reports.view", "reports.export",
        "staff.performance.view", "staff.performance.evaluate",
        "platform.view", "finance.view", "sales.view", "customers.view",
    ],
}


def bootstrap_roles_and_permissions(stdout=None) -> dict[str, Permission]:
    write = stdout.write if stdout else (lambda msg: None)

    write("Bootstrapping permissions...\n")
    perm_map = {}
    for codename, name, module in PERMISSIONS:
        perm, _ = Permission.objects.get_or_create(
            codename=codename,
            defaults={"name": name, "module": module},
        )
        perm_map[codename] = perm

    write("Bootstrapping roles...\n")
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

    return perm_map
