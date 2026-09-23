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
    ("inventory.cross_branch_view", "View Stock Availability In Other Branches", "inventory"),
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
    ("gym.members.create", "Create Gym Members", "gym"),
    ("gym.members.update", "Update Gym Members", "gym"),
    ("gym.members.delete", "Delete Gym Members", "gym"),
    ("gym.attendance.checkin", "Check In Gym Members", "gym"),
    ("gym.member_portal", "Access Gym Member Mobile App", "gym"),
    ("restaurant.view", "View Restaurant Module", "restaurant"),
    ("restaurant.manage", "Manage Restaurant Floor & Menus", "restaurant"),
    ("restaurant.menu.create", "Create Restaurant Menu", "restaurant"),
    ("restaurant.menu.update", "Update Restaurant Menu", "restaurant"),
    ("restaurant.menu.delete", "Delete Restaurant Menu", "restaurant"),
    ("restaurant.tables.create", "Create Dining Tables", "restaurant"),
    ("restaurant.tables.update", "Update Dining Tables", "restaurant"),
    ("restaurant.tables.delete", "Delete Dining Tables", "restaurant"),
    ("restaurant.kitchen", "Kitchen Display / Prep", "restaurant"),
    ("restaurant.floor", "Floor Service / Waiter Ops", "restaurant"),
    ("restaurant.orders.create", "Create Restaurant Orders", "restaurant"),
    ("restaurant.orders.update", "Update Restaurant Orders", "restaurant"),
    ("restaurant.orders.cancel", "Cancel Restaurant Orders", "restaurant"),
    ("restaurant.orders.void", "Void Restaurant Orders", "restaurant"),
    ("restaurant.orders.refund", "Refund Restaurant Orders", "restaurant"),
    ("cafeteria.dashboard.view", "View Cafeteria Dashboard", "restaurant"),
    ("cafeteria.pos.use", "Use Cafeteria POS", "restaurant"),
    ("cafeteria.settings.view", "View Cafeteria Settings", "restaurant"),
    ("cafeteria.settings.update", "Update Cafeteria Settings", "restaurant"),
    ("cafeteria.barista.queue", "Barista Queue / Board", "restaurant"),
    ("cafeteria.waste.view", "View Cafeteria Waste", "restaurant"),
    ("cafeteria.waste.create", "Create Cafeteria Waste", "restaurant"),
    ("cafeteria.waste.approve", "Approve Cafeteria Waste", "restaurant"),
    ("cafeteria.recipes.view", "View Cafeteria Recipes", "restaurant"),
    ("cafeteria.recipes.create", "Create Cafeteria Recipes", "restaurant"),
    ("cafeteria.recipes.update", "Update Cafeteria Recipes", "restaurant"),
    ("cafeteria.staff.view", "View Barista Staff", "restaurant"),
    ("cafeteria.staff.manage", "Manage Barista Staff", "restaurant"),
    ("hotel.view", "View Hotel Module", "hotel"),
    ("hotel.manage", "Manage Hotel Rooms & Rates", "hotel"),
    ("hotel.rooms.create", "Create Hotel Rooms", "hotel"),
    ("hotel.rooms.update", "Update Hotel Rooms", "hotel"),
    ("hotel.rooms.delete", "Delete Hotel Rooms", "hotel"),
    ("hotel.guests.create", "Create Hotel Guests", "hotel"),
    ("hotel.guests.update", "Update Hotel Guests", "hotel"),
    ("hotel.guests.delete", "Delete Hotel Guests", "hotel"),
    ("hotel.reservations.create", "Create Hotel Reservations", "hotel"),
    ("hotel.reservations.update", "Update Hotel Reservations", "hotel"),
    ("hotel.front_desk", "Front Desk / Reservations", "hotel"),
    ("hotel.housekeeping", "Housekeeping Room Status", "hotel"),
    ("property_management.view", "View Property Management", "property_management"),
    ("property_management.manage", "Manage Properties & Units", "property_management"),
    ("property_management.masters.create", "Create Property Masters", "property_management"),
    ("property_management.masters.update", "Update Property Masters", "property_management"),
    ("property_management.masters.delete", "Delete Property Masters", "property_management"),
    ("property_management.maintenance", "Property Maintenance Ops", "property_management"),
    ("housing_rental.view", "View Housing Rental", "housing_rental"),
    ("housing_rental.manage", "Manage Housing Leases", "housing_rental"),
    ("housing_rental.tenants.create", "Create Housing Tenants", "housing_rental"),
    ("housing_rental.tenants.update", "Update Housing Tenants", "housing_rental"),
    ("housing_rental.tenants.delete", "Delete Housing Tenants", "housing_rental"),
    ("office_rental.view", "View Office Rental", "office_rental"),
    ("office_rental.manage", "Manage Office Leases", "office_rental"),
    ("office_rental.tenants.create", "Create Office Tenants", "office_rental"),
    ("office_rental.tenants.update", "Update Office Tenants", "office_rental"),
    ("office_rental.tenants.delete", "Delete Office Tenants", "office_rental"),
    ("projects.view", "View Project Management", "project_management"),
    ("projects.create", "Create Projects", "project_management"),
    ("projects.update", "Update Projects", "project_management"),
    ("projects.delete", "Delete Projects", "project_management"),
    ("projects.archive", "Archive Projects", "project_management"),
    ("projects.approve", "Approve Project Workflow", "project_management"),
    ("project.budget.view", "View Project Budgets", "project_management"),
    ("project.budget.create", "Create Project Budgets", "project_management"),
    ("project.budget.update", "Update Project Budgets", "project_management"),
    ("project.budget.approve", "Approve Project Budgets", "project_management"),
    ("project.boq.view", "View Project BOQs", "project_management"),
    ("project.boq.create", "Create Project BOQs", "project_management"),
    ("project.boq.update", "Update Project BOQs", "project_management"),
    ("project.boq.approve", "Approve Project BOQs", "project_management"),
    ("project.wbs.view", "View Project WBS", "project_management"),
    ("project.wbs.create", "Create Project WBS Nodes", "project_management"),
    ("project.wbs.update", "Update Project WBS Nodes", "project_management"),
    ("project.wbs.delete", "Delete Project WBS Nodes", "project_management"),
    ("project.tasks.view", "View Project Tasks", "project_management"),
    ("project.tasks.create", "Create Project Tasks", "project_management"),
    ("project.tasks.update", "Update Project Tasks", "project_management"),
    ("project.tasks.delete", "Delete Project Tasks", "project_management"),
    ("project.milestones.view", "View Project Milestones", "project_management"),
    ("project.milestones.create", "Create Project Milestones", "project_management"),
    ("project.milestones.update", "Update Project Milestones", "project_management"),
    ("project.milestones.delete", "Delete Project Milestones", "project_management"),
    ("project.workers.view", "View Project Workers", "project_management"),
    ("project.workers.create", "Create Project Workers", "project_management"),
    ("project.workers.assign", "Assign Workers to Projects", "project_management"),
    ("project.workers.remove", "Remove Workers from Projects", "project_management"),
    ("project.wages.view", "View Project Wages", "project_management"),
    ("project.wages.create", "Create Project Wages", "project_management"),
    ("project.wages.approve", "Approve Project Wages", "project_management"),
    ("project.wages.pay", "Pay Project Wages", "project_management"),
    ("project.procurement.create", "Create Project Procurement", "project_management"),
    ("project.procurement.approve", "Approve Project Procurement", "project_management"),
    ("project.procurement.receive", "Receive Project Procurement", "project_management"),
    ("project.change_orders.create", "Create Project Change Orders", "project_management"),
    ("project.change_orders.approve", "Approve Project Change Orders", "project_management"),
    *[(f"project.{area}.{action}", f"{action.title()} Project {area.replace('_', ' ').title()}", "project_management")
      for area in ("materials", "inventory", "equipment", "expenses", "change_orders", "site_reports", "quality", "safety", "risks", "issues", "invoices")
      for action in ("view", "create", "update", "delete")],
    ("project.finance.view", "View Project Finance", "project_management"),
    *[(f"travel.{area}.{action}", f"{action.title()} Travel {area.replace('_', ' ').title()}", "travel_agency")
      for area in ("destinations", "packages", "travelers", "flights", "hotels", "visas", "commissions", "insurance", "vehicles", "drivers", "transfers", "itineraries", "activities", "quotations", "documents", "payments", "refunds", "expenses")
      for action in ("view", "create", "update", "delete")],
    ("travel.bookings.view", "View Travel Bookings", "travel_agency"),
    ("travel.bookings.create", "Create Travel Bookings", "travel_agency"),
    ("travel.bookings.update", "Update Travel Bookings", "travel_agency"),
    ("travel.bookings.cancel", "Cancel Travel Bookings", "travel_agency"),
    ("travel.payments.create", "Create Travel Payments", "travel_agency"),
    ("travel.refund", "Refund Travel Bookings", "travel_agency"),
    *[(f"travel.{area}.post_accounting", f"Post Travel {area.title()} to Accounting", "travel_agency") for area in ("payments", "refunds")],
    ("travel.commissions.approve", "Approve Travel Commissions", "travel_agency"),
    ("travel.commissions.pay", "Pay Travel Commissions", "travel_agency"),
    ("travel.bookings.post_accounting", "Post Travel Bookings to Accounting", "travel_agency"),
    *[
        (
            f"travel.{area}.{action}",
            f"{action.title()} Travel {area.replace('_', ' ').title()}",
            "travel_agency",
        )
        for area in ("destinations", "packages", "travelers", "flights", "hotels", "visa", "commission")
        for action in ("view", "create", "update", "delete")
        if f"travel.{area}.{action}"
        not in {
            "travel.packages.create", "travel.packages.update",
            "travel.visa.create", "travel.visa.update",
            "travel.commission.view",
        }
    ],
    ("school.view", "View School Workspace", "school"),
    ("school.manage", "Manage School Module", "school"),
    ("school.settings.view", "View School Settings", "school"),
    ("school.settings.update", "Update School Settings", "school"),
    ("school.academic.view", "View Academic Structure", "school"),
    ("school.academic.create", "Create Academic Records", "school"),
    ("school.academic.update", "Update Academic Records", "school"),
    ("school.academic.archive", "Archive Academic Records", "school"),
    ("school.academic.activate", "Activate Academic Year", "school"),
    ("trash.view", "View Trash / Deleted Records", "trash"),
    ("trash.restore", "Restore or Permanently Delete Trash", "trash"),
    ("organization.view", "View Branch Structure", "organization"),
    ("organization.manage", "Manage Terminals, Registers & Locations", "organization"),
    ("branch.access.view", "View Branch Access & Profiles", "organization"),
    ("branch.access.manage", "Grant or Revoke Branch Access", "organization"),
    ("integrations.view", "View Integrations & SMS Logs", "integrations"),
    ("integrations.manage", "Manage Integration Credentials, SMS Providers & Templates", "integrations"),
    ("integrations.sms.send", "Send SMS", "integrations"),
    ("integrations.sms.billing.view", "View SMS Packages, Balance & Usage", "integrations"),
    ("integrations.sms.billing.purchase", "Buy SMS Packages", "integrations"),
    ("billing.subscription.view", "View Plan, Subscription Invoices & Payments", "billing"),
    ("billing.subscription.pay", "Pay / Renew / Change ERP Subscription", "billing"),
    ("integrations.payments.view", "View Payment Intents & Reconciliation", "integrations"),
    ("integrations.payments.collect", "Start Provider Payments on Invoices", "integrations"),
    ("integrations.payments.reconcile", "Run & Resolve Payment Reconciliation", "integrations"),
]

ROLE_PERMISSIONS = {
    "platform_admin": "*",
    "super_admin": "*",
    "admin": [
        "dashboard.view", "pos.access", "products.view", "products.create",
        "products.update", "products.delete", "inventory.view", "inventory.adjust",
        "inventory.transfer", "inventory.cross_branch_view",
        "purchases.view", "purchases.create", "purchases.update",
        "sales.view", "sales.create", "sales.update", "sales.delete", "sales.refund",
        "customers.view", "customers.create", "customers.update",
        "suppliers.view", "suppliers.create", "suppliers.update",
        "finance.view", "finance.create", "finance.approve", "reports.view", "reports.export",
        "users.view", "users.create", "users.update", "users.delete",
        "roles.view", "branches.view", "branches.create", "branches.update",
        "organization.view", "organization.manage",
        "branch.access.view", "branch.access.manage",
        "integrations.view", "integrations.manage", "integrations.sms.send",
        "integrations.sms.billing.view", "integrations.sms.billing.purchase",
        "billing.subscription.view", "billing.subscription.pay",
        "integrations.payments.view", "integrations.payments.collect", "integrations.payments.reconcile",
        "settings.view", "settings.update", "audit.view",
        "staff.performance.view", "staff.performance.evaluate",
        "futsal.view", "futsal.manage", "futsal.finance",
        "pharmacy.view", "pharmacy.manage", "pharmacy.dispense",
        "gym.view", "gym.manage", "gym.members.create", "gym.members.update", "gym.members.delete",
        "gym.attendance.checkin",
        "restaurant.view", "restaurant.manage",
        "restaurant.menu.create", "restaurant.menu.update", "restaurant.menu.delete",
        "restaurant.tables.create", "restaurant.tables.update", "restaurant.tables.delete",
        "restaurant.kitchen", "restaurant.floor",
        "restaurant.orders.create", "restaurant.orders.update", "restaurant.orders.cancel",
        "restaurant.orders.void", "restaurant.orders.refund",
        "cafeteria.dashboard.view", "cafeteria.pos.use", "cafeteria.settings.view", "cafeteria.settings.update",
        "cafeteria.barista.queue", "cafeteria.waste.view", "cafeteria.waste.create", "cafeteria.waste.approve",
        "cafeteria.recipes.view", "cafeteria.recipes.create", "cafeteria.recipes.update",
        "cafeteria.staff.view", "cafeteria.staff.manage",
        "hotel.view", "hotel.manage",
        "hotel.rooms.create", "hotel.rooms.update", "hotel.rooms.delete",
        "hotel.guests.create", "hotel.guests.update", "hotel.guests.delete",
        "hotel.reservations.create", "hotel.reservations.update",
        "hotel.front_desk", "hotel.housekeeping",
        "property_management.view", "property_management.manage",
        "property_management.masters.create", "property_management.masters.update",
        "property_management.masters.delete", "property_management.maintenance",
        "housing_rental.view", "housing_rental.manage",
        "housing_rental.tenants.create", "housing_rental.tenants.update", "housing_rental.tenants.delete",
        "office_rental.view", "office_rental.manage",
        "office_rental.tenants.create", "office_rental.tenants.update", "office_rental.tenants.delete",
        "projects.view", "projects.create", "projects.update", "projects.delete", "projects.archive", "projects.approve",
        "project.budget.view", "project.budget.create", "project.budget.update", "project.budget.approve",
        "project.boq.view", "project.boq.create", "project.boq.update", "project.boq.approve",
        "project.wbs.view", "project.wbs.create", "project.wbs.update", "project.wbs.delete",
        "project.tasks.view", "project.tasks.create", "project.tasks.update", "project.tasks.delete",
        "project.milestones.view", "project.milestones.create", "project.milestones.update", "project.milestones.delete",
        "project.workers.view", "project.workers.create", "project.workers.assign", "project.workers.remove",
        "project.wages.view", "project.wages.create", "project.wages.approve", "project.wages.pay",
        "project.procurement.create", "project.procurement.approve", "project.procurement.receive",
        "project.change_orders.create", "project.change_orders.approve", "project.finance.view",
        *[f"project.{area}.{action}" for area in ("materials", "inventory", "equipment", "expenses", "change_orders", "site_reports", "quality", "safety", "risks", "issues", "invoices") for action in ("view", "create", "update", "delete")],
        *[f"travel.{area}.{action}" for area in ("destinations", "packages", "travelers", "flights", "hotels", "visas", "commissions", "insurance", "vehicles", "drivers", "transfers", "itineraries", "activities", "quotations", "documents", "payments", "refunds", "expenses") for action in ("view", "create", "update", "delete")],
        "travel.bookings.view", "travel.bookings.create", "travel.bookings.update", "travel.bookings.cancel",
        "travel.payments.create", "travel.refund", "travel.payments.post_accounting", "travel.refunds.post_accounting", "travel.commissions.approve", "travel.commissions.pay",
        "travel.bookings.post_accounting",
        "school.view", "school.manage", "school.settings.view", "school.settings.update",
        "school.academic.view", "school.academic.create", "school.academic.update",
        "school.academic.archive", "school.academic.activate",
        "trash.view", "trash.restore",
    ],
    "branch_manager": [
        "dashboard.view", "pos.access", "products.view", "products.create",
        "products.update", "inventory.view", "inventory.adjust", "inventory.transfer",
        "inventory.cross_branch_view",
        "purchases.view", "purchases.create", "purchases.update",
        "sales.view", "sales.create", "sales.update",
        "customers.view", "customers.create", "suppliers.view", "reports.view",
        "finance.view", "finance.create", "finance.approve",
        "users.view", "branches.view", "settings.view",
        "organization.view", "organization.manage", "branch.access.view",
        "staff.performance.view", "staff.performance.evaluate",
        "futsal.view", "futsal.manage", "futsal.finance",
        "pharmacy.view", "pharmacy.manage", "pharmacy.dispense",
        "gym.view", "gym.manage", "gym.members.create", "gym.members.update", "gym.members.delete",
        "gym.attendance.checkin",
        "restaurant.view", "restaurant.manage",
        "restaurant.menu.create", "restaurant.menu.update", "restaurant.menu.delete",
        "restaurant.tables.create", "restaurant.tables.update", "restaurant.tables.delete",
        "restaurant.kitchen", "restaurant.floor",
        "restaurant.orders.create", "restaurant.orders.update", "restaurant.orders.cancel",
        "restaurant.orders.void", "restaurant.orders.refund",
        "cafeteria.dashboard.view", "cafeteria.pos.use", "cafeteria.settings.view", "cafeteria.settings.update",
        "cafeteria.barista.queue", "cafeteria.waste.view", "cafeteria.waste.create", "cafeteria.waste.approve",
        "cafeteria.recipes.view", "cafeteria.recipes.create", "cafeteria.recipes.update",
        "cafeteria.staff.view", "cafeteria.staff.manage",
        "hotel.view", "hotel.manage",
        "hotel.rooms.create", "hotel.rooms.update", "hotel.rooms.delete",
        "hotel.guests.create", "hotel.guests.update", "hotel.guests.delete",
        "hotel.reservations.create", "hotel.reservations.update",
        "hotel.front_desk", "hotel.housekeeping",
        "property_management.view", "property_management.manage",
        "property_management.masters.create", "property_management.masters.update",
        "property_management.masters.delete", "property_management.maintenance",
        "housing_rental.view", "housing_rental.manage",
        "housing_rental.tenants.create", "housing_rental.tenants.update", "housing_rental.tenants.delete",
        "office_rental.view", "office_rental.manage",
        "office_rental.tenants.create", "office_rental.tenants.update", "office_rental.tenants.delete",
        "projects.view", "projects.create", "projects.update", "projects.archive",
        "project.budget.view", "project.budget.create", "project.budget.update",
        "project.boq.view", "project.boq.create", "project.boq.update", "project.boq.approve",
        "project.wbs.view", "project.wbs.create", "project.wbs.update",
        "project.tasks.view", "project.tasks.create", "project.tasks.update", "project.tasks.delete",
        "project.milestones.view", "project.milestones.create", "project.milestones.update", "project.milestones.delete",
        "project.workers.view", "project.workers.create", "project.workers.assign",
        "project.wages.view", "project.wages.create", "project.wages.approve",
        "project.procurement.create", "project.procurement.approve", "project.procurement.receive",
        "project.change_orders.create", "project.change_orders.approve", "project.finance.view",
        *[f"project.{area}.{action}" for area in ("materials", "inventory", "equipment", "expenses", "change_orders", "site_reports", "quality", "safety", "risks", "issues", "invoices") for action in ("view", "create", "update", "delete")],
        *[f"travel.{area}.{action}" for area in ("destinations", "packages", "travelers", "flights", "hotels", "visas", "commissions", "insurance", "vehicles", "drivers", "transfers", "itineraries", "activities", "quotations", "documents", "payments", "refunds", "expenses") for action in ("view", "create", "update", "delete")],
        "travel.bookings.view", "travel.bookings.create", "travel.bookings.update", "travel.bookings.cancel",
        "travel.payments.create", "travel.payments.post_accounting", "travel.refunds.post_accounting", "travel.commissions.approve",
        "travel.bookings.post_accounting",
        "school.view", "school.manage", "school.settings.view", "school.settings.update",
        "school.academic.view", "school.academic.create", "school.academic.update",
        "school.academic.archive", "school.academic.activate",
        "trash.view",
    ],
    "accountant": [
        "dashboard.view", "finance.view", "finance.create", "finance.approve", "reports.view",
        "reports.export", "sales.view", "purchases.view",
    ],
    "inventory_manager": [
        "dashboard.view", "products.view", "products.create", "products.update",
        "inventory.view", "inventory.adjust", "inventory.transfer", "inventory.cross_branch_view",
        "purchases.view", "purchases.create", "suppliers.view", "reports.view",
    ],
    "cashier": [
        "pos.access", "products.view", "customers.view", "sales.view", "sales.create",
        "sales.refund", "inventory.cross_branch_view",
    ],
    "sales_staff": [
        "dashboard.view", "pos.access", "sales.view", "sales.create",
        "customers.view", "customers.create", "products.view", "inventory.cross_branch_view",
    ],
    "read_only": [
        "dashboard.view", "products.view", "inventory.view", "inventory.cross_branch_view", "sales.view",
        "customers.view", "suppliers.view", "finance.view", "reports.view", "projects.view", "project.wbs.view", "travel.bookings.view",
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
        "dashboard.view", "pos.access", "products.view", "inventory.view", "inventory.cross_branch_view",
        "pharmacy.view", "pharmacy.manage", "pharmacy.dispense",
        "customers.view", "customers.create", "sales.view", "sales.create",
    ],
    "gym_manager": [
        "dashboard.view", "gym.view", "gym.manage",
        "gym.members.create", "gym.members.update", "gym.members.delete",
        "gym.attendance.checkin",
        "customers.view", "customers.create", "pos.access", "sales.view",
        "sales.create", "reports.view", "finance.view",
    ],
    "receptionist": [
        "dashboard.view", "customers.view", "customers.create",
        "gym.view", "gym.members.create", "gym.members.update",
        "gym.attendance.checkin", "pos.access", "sales.view", "sales.create",
    ],
    "trainer": [
        "dashboard.view", "gym.view", "gym.attendance.checkin", "customers.view",
    ],
    "gym_member": [
        "gym.member_portal",
    ],
    "waiter": [
        "pos.access", "restaurant.view", "restaurant.floor",
        "restaurant.orders.create", "restaurant.orders.update", "restaurant.orders.cancel",
        "customers.view", "customers.create", "products.view", "sales.view", "sales.create",
    ],
    "kitchen": [
        "restaurant.view", "restaurant.kitchen", "restaurant.orders.update", "products.view",
        "cafeteria.barista.queue",
    ],
    "cafeteria_cashier": [
        "pos.access", "cafeteria.pos.use", "cafeteria.dashboard.view",
        "customers.view", "customers.create", "products.view",
        "restaurant.view", "restaurant.floor", "restaurant.orders.create", "restaurant.orders.update",
    ],
    "barista": [
        "dashboard.view", "cafeteria.dashboard.view", "cafeteria.barista.queue",
        "restaurant.view", "restaurant.kitchen", "restaurant.orders.update",
        "products.view",
    ],
    "front_desk": [
        "dashboard.view", "hotel.view", "hotel.front_desk",
        "hotel.guests.create", "hotel.guests.update",
        "hotel.reservations.create", "hotel.reservations.update",
        "customers.view", "customers.create", "pos.access", "sales.view", "sales.create",
    ],
    "housekeeping": [
        "dashboard.view", "hotel.view", "hotel.housekeeping",
    ],
    "property_manager": [
        "dashboard.view",
        "property_management.view",
        "property_management.manage",
        "property_management.masters.create",
        "property_management.masters.update",
        "property_management.masters.delete",
        "property_management.maintenance",
        "housing_rental.view",
        "housing_rental.manage",
        "housing_rental.tenants.create",
        "housing_rental.tenants.update",
        "housing_rental.tenants.delete",
        "office_rental.view",
        "office_rental.manage",
        "office_rental.tenants.create",
        "office_rental.tenants.update",
        "office_rental.tenants.delete",
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


from apps.school.permissions import FOUNDATION_PERMISSIONS
PERMISSIONS.extend(FOUNDATION_PERMISSIONS)
_school_codes = [c for c, _, _ in FOUNDATION_PERMISSIONS]
_school_reads = [c for c in _school_codes if c.endswith(".view") and ".campus_access." not in c]
for _slug in ("school_owner", "school_admin"):
    ROLE_PERMISSIONS[_slug] = ["school.view", *_school_codes]
for _slug in ("school_principal", "school_academic_director", "school_registrar"):
    ROLE_PERMISSIONS[_slug] = ["school.view", *[c for c in _school_codes if ".campus_access." not in c and c != "school.campus.all" and (not c.startswith("school.campus.") or c == "school.campus.view")]]
ROLE_PERMISSIONS["school_registrar"] = [c for c in ROLE_PERMISSIONS["school_registrar"] if c not in ("school.teacher.assignable", "school.leadership.assignable")]
ROLE_PERMISSIONS["school_teacher"] = ["school.view", "school.teacher.assignable", *_school_reads]

from apps.school.sis_permissions import SIS_PERMISSIONS
PERMISSIONS.extend(SIS_PERMISSIONS)
_sis_codes = [code for code, _, _ in SIS_PERMISSIONS]
for _slug in ("school_owner", "school_admin", "school_principal", "school_academic_director", "school_registrar"):
    ROLE_PERMISSIONS[_slug].extend(_sis_codes if _slug in ("school_owner", "school_admin") else [code for code in _sis_codes if "override" not in code and "confidential" not in code and ".admission_policy." not in code])
ROLE_PERMISSIONS["school_teacher"].extend(["school.student.view", "school.enrollment.view"])
ROLE_PERMISSIONS["school_teacher"].extend(["school.attendance.view", "school.attendance.take", "school.attendance_record.view", "school.attendance_correction.request", "school.timetable.view", "school.timetable_entry.view", "school.period.view", "school.classroom.view", "school.teacher_assignment.view", "school.staff_profile.view"])

ROLE_PERMISSIONS["school_teacher"].extend([
    "school.assignment.view", "school.assignment.create", "school.assignment.update", "school.assignment.publish", "school.assignment.close",
    "school.submission.view", "school.submission.create", "school.submission.update", "school.submission.grade",
    "school.exam.view", "school.academic_assessment.view", "school.exam_schedule.view", "school.mark.view", "school.mark.enter",
    "school.grade_scheme.view", "school.grade_band.view",
])

# Phase 6 financial privileges are explicit; teacher grants remain unchanged.
for _slug in ('school_owner','school_admin'):
    ROLE_PERMISSIONS[_slug].extend(['finance.view','finance.create','finance.approve','sales.view','sales.create','customers.view','customers.create','customers.update'])

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

    from apps.authentication.models import User

    for user in User.objects.filter(deleted_at__isnull=True, role__slug__in=Role.ELEVATED_SLUGS):
        if user.apply_elevated_flags():
            user.save(update_fields=["is_platform_admin", "is_superuser", "is_staff"])
            write(f"  Synced elevated flags for '{user.username}'.\n")

    return perm_map
