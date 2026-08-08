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
    ("purchases.update", "Update Purchases", "purchases"),
    ("sales.view", "View Sales", "sales"),
    ("sales.create", "Create Sales", "sales"),
    ("sales.update", "Update Sales / Receipts", "sales"),
    ("sales.delete", "Delete Sales / Receipts", "sales"),
    ("sales.refund", "Refund POS Sales", "sales"),
    ("customers.view", "View Customers", "customers"),
    ("customers.create", "Create Customers", "customers"),
    ("customers.update", "Update Customers", "customers"),
    ("suppliers.view", "View Suppliers", "suppliers"),
    ("suppliers.create", "Create Suppliers", "suppliers"),
    ("suppliers.update", "Update Suppliers", "suppliers"),
    ("finance.view", "View Finance", "finance"),
    ("finance.create", "Create Finance Entries", "finance"),
    ("finance.approve", "Approve / Post Draft Journals", "finance"),
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
    ("pharmacy.view", "View Pharmacy Module", "pharmacy"),
    ("pharmacy.manage", "Manage Pharmacy Catalog & Batches", "pharmacy"),
    ("pharmacy.dispense", "Dispense Prescriptions", "pharmacy"),
    ("gym.view", "View Gym Module", "gym"),
    ("gym.manage", "Manage Gym Members & Plans", "gym"),
    ("gym.attendance.checkin", "Check In Gym Members", "gym"),
    ("gym.member_portal", "Access Gym Member Mobile App", "gym"),
    ("restaurant.view", "View Restaurant Module", "restaurant"),
    ("restaurant.manage", "Manage Restaurant Floor & Menus", "restaurant"),
    ("restaurant.kitchen", "Kitchen Display / Prep", "restaurant"),
    ("restaurant.floor", "Floor Service / Waiter Ops", "restaurant"),
    ("hotel.view", "View Hotel Module", "hotel"),
    ("hotel.manage", "Manage Hotel Rooms & Rates", "hotel"),
    ("hotel.front_desk", "Front Desk / Reservations", "hotel"),
    ("hotel.housekeeping", "Housekeeping Room Status", "hotel"),
    ("property_management.view", "View Property Management", "property_management"),
    ("property_management.manage", "Manage Properties & Units", "property_management"),
    ("property_management.maintenance", "Property Maintenance Ops", "property_management"),
    ("housing_rental.view", "View Housing Rental", "housing_rental"),
    ("housing_rental.manage", "Manage Housing Leases", "housing_rental"),
    ("office_rental.view", "View Office Rental", "office_rental"),
    ("office_rental.manage", "Manage Office Leases", "office_rental"),
    ("trash.view", "View Trash / Deleted Records", "trash"),
    ("trash.restore", "Restore or Permanently Delete Trash", "trash"),
]

ROLE_PERMISSIONS = {
    "platform_admin": "*",
    "super_admin": "*",
    "admin": [
        "dashboard.view", "pos.access", "products.view", "products.create",
        "products.update", "products.delete", "inventory.view", "inventory.adjust",
        "inventory.transfer", "purchases.view", "purchases.create", "purchases.update",
        "sales.view", "sales.create", "sales.update", "sales.delete", "sales.refund",
        "customers.view", "customers.create", "customers.update",
        "suppliers.view", "suppliers.create", "suppliers.update",
        "finance.view", "finance.create", "finance.approve", "reports.view", "reports.export",
        "users.view", "users.create", "users.update",
        "roles.view", "branches.view", "branches.create", "branches.update",
        "settings.view", "settings.update", "audit.view",
        "staff.performance.view", "staff.performance.evaluate",
        "futsal.view", "futsal.manage", "futsal.finance",
        "pharmacy.view", "pharmacy.manage", "pharmacy.dispense",
        "gym.view", "gym.manage", "gym.attendance.checkin",
        "restaurant.view", "restaurant.manage", "restaurant.kitchen", "restaurant.floor",
        "hotel.view", "hotel.manage", "hotel.front_desk", "hotel.housekeeping",
        "property_management.view", "property_management.manage", "property_management.maintenance",
        "housing_rental.view", "housing_rental.manage",
        "office_rental.view", "office_rental.manage",
        "trash.view", "trash.restore",
    ],
    "branch_manager": [
        "dashboard.view", "pos.access", "products.view", "products.create",
        "products.update", "inventory.view", "inventory.adjust", "inventory.transfer",
        "purchases.view", "purchases.create", "purchases.update",
        "sales.view", "sales.create", "sales.update",
        "customers.view", "customers.create", "suppliers.view", "reports.view",
        "finance.view", "finance.create", "finance.approve",
        "users.view", "branches.view", "settings.view",
        "staff.performance.view", "staff.performance.evaluate",
        "futsal.view", "futsal.manage", "futsal.finance",
        "pharmacy.view", "pharmacy.manage", "pharmacy.dispense",
        "gym.view", "gym.manage", "gym.attendance.checkin",
        "restaurant.view", "restaurant.manage", "restaurant.kitchen", "restaurant.floor",
        "hotel.view", "hotel.manage", "hotel.front_desk", "hotel.housekeeping",
        "property_management.view", "property_management.manage", "property_management.maintenance",
        "housing_rental.view", "housing_rental.manage",
        "office_rental.view", "office_rental.manage",
        "trash.view",
    ],
    "accountant": [
        "dashboard.view", "finance.view", "finance.create", "finance.approve", "reports.view",
        "reports.export", "sales.view", "purchases.view",
    ],
    "inventory_manager": [
        "dashboard.view", "products.view", "products.create", "products.update",
        "inventory.view", "inventory.adjust", "inventory.transfer",
        "purchases.view", "purchases.create", "suppliers.view", "reports.view",
    ],
    "cashier": ["pos.access", "products.view", "customers.view", "sales.view", "sales.create", "sales.refund"],
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
    "pharmacist": [
        "dashboard.view", "pos.access", "products.view", "inventory.view",
        "pharmacy.view", "pharmacy.manage", "pharmacy.dispense",
        "customers.view", "customers.create", "sales.view", "sales.create",
    ],
    "gym_manager": [
        "dashboard.view", "gym.view", "gym.manage", "gym.attendance.checkin",
        "customers.view", "customers.create", "pos.access", "sales.view",
        "sales.create", "reports.view", "finance.view",
    ],
    "receptionist": [
        "dashboard.view", "customers.view", "customers.create",
        "gym.view", "gym.attendance.checkin", "pos.access", "sales.view", "sales.create",
    ],
    "trainer": [
        "dashboard.view", "gym.view", "gym.attendance.checkin", "customers.view",
    ],
    "gym_member": [
        "gym.member_portal",
    ],
    "waiter": [
        "pos.access", "restaurant.view", "restaurant.floor",
        "customers.view", "customers.create", "products.view", "sales.view", "sales.create",
    ],
    "kitchen": [
        "restaurant.view", "restaurant.kitchen", "products.view",
    ],
    "cafeteria_cashier": [
        "pos.access", "customers.view", "customers.create", "products.view",
        "restaurant.view", "restaurant.floor",
    ],
    "front_desk": [
        "dashboard.view", "hotel.view", "hotel.front_desk",
        "customers.view", "customers.create", "pos.access", "sales.view", "sales.create",
    ],
    "housekeeping": [
        "dashboard.view", "hotel.view", "hotel.housekeeping",
    ],
    "property_manager": [
        "dashboard.view",
        "property_management.view",
        "property_management.manage",
        "property_management.maintenance",
        "housing_rental.view",
        "housing_rental.manage",
        "office_rental.view",
        "office_rental.manage",
        "customers.view",
        "customers.create",
        "reports.view",
        "finance.view",
    ],
    "property_maintenance": [
        "dashboard.view",
        "property_management.view",
        "property_management.maintenance",
    ],
    "shop_group_manager": [
        "dashboard.view", "reports.view", "reports.export",
        "staff.performance.view", "staff.performance.evaluate",
        "platform.view", "platform.manage",
        "finance.view", "finance.create", "finance.approve", "sales.view", "sales.update", "sales.delete",
        "customers.view",
        "users.view", "users.create", "users.update",
        "roles.view",
        "products.view", "inventory.view",
        "trash.view", "trash.restore",
    ],
}


def bootstrap_roles_and_permissions(stdout=None, *, reset_role_permissions: bool = False) -> dict[str, Permission]:
    """
    Ensure system permissions and roles exist.

    By default this is **additive**: new default permissions are added to roles,
    but custom permissions assigned in Admin are never removed.

    Pass reset_role_permissions=True (or bootstrap_system --reset-role-permissions)
    to wipe each system role back to the built-in ROLE_PERMISSIONS list.
    """
    write = stdout.write if stdout else (lambda msg: None)

    write("Bootstrapping permissions...\n")
    perm_map = {}
    for codename, name, module in PERMISSIONS:
        perm, _ = Permission.objects.get_or_create(
            codename=codename,
            defaults={"name": name, "module": module},
        )
        # Keep catalog labels in sync without touching role assignments
        if perm.name != name or perm.module != module:
            perm.name = name
            perm.module = module
            perm.save(update_fields=["name", "module", "updated_at"])
        perm_map[codename] = perm

    write("Bootstrapping roles...\n")
    for slug, name in Role.SYSTEM_ROLES:
        role, created = Role.objects.get_or_create(
            slug=slug,
            defaults={"name": name, "is_system": True},
        )
        if not role.is_system:
            role.is_system = True
            role.save(update_fields=["is_system", "updated_at"])

        codes = ROLE_PERMISSIONS.get(slug, [])
        if codes == "*":
            codes = list(perm_map.keys())

        if reset_role_permissions:
            write(f"  Resetting permissions for role '{slug}' to defaults...\n")
            RolePermission.objects.filter(role=role).delete()

        for code in codes:
            if code in perm_map:
                RolePermission.objects.get_or_create(
                    role=role, permission=perm_map[code]
                )

        if created:
            write(f"  Created role '{slug}'.\n")

    return perm_map
