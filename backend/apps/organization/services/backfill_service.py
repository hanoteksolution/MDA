"""Branch backfills (migration plan §4.1 – §4.3).

Written once and called from two places: the data migrations in wave M1 and the
``backfill_branch_access`` management command, so a re-run on production uses
exactly the code the migration used.

Every function is **idempotent**, **derives** rather than guesses, and returns a
``BackfillResult`` with total / resolved / unresolved / skipped / ambiguous /
review_required counts. Nothing here invents a Company, a branch attribution, or a
School permission.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Locations created for every warehouse. Mirrors ``structure_service.DEFAULT_LOCATIONS``
#: but is duplicated deliberately: historical models in a migration have no services.
DEFAULT_LOCATION_SPECS = [
    ("MAIN", "Main Storage", "STORAGE", True, True, 0),
    ("FLOOR", "Shop Floor", "SHOP_FLOOR", True, False, 1),
    ("RECV", "Receiving", "RECEIVING", False, False, 2),
    ("DAMAGED", "Damaged Goods", "DAMAGED", False, False, 3),
]

TRANSIT_LOCATION = ("TRANSIT", "In Transit", "TRANSIT", False, False, 4)

MANAGER_ROLE_SLUGS = {"branch_manager", "admin"}


@dataclass
class BackfillResult:
    name: str
    total: int = 0
    resolved: int = 0
    unresolved: int = 0
    skipped: int = 0
    ambiguous: int = 0
    review_required: int = 0
    details: list[str] = field(default_factory=list)

    def as_dict(self):
        return {
            "backfill": self.name,
            "total": self.total,
            "resolved": self.resolved,
            "unresolved": self.unresolved,
            "skipped": self.skipped,
            "ambiguous": self.ambiguous,
            "review_required": self.review_required,
            "details": self.details,
        }

    def __str__(self):
        return (
            f"{self.name}: total={self.total} resolved={self.resolved} "
            f"unresolved={self.unresolved} skipped={self.skipped} "
            f"ambiguous={self.ambiguous} review_required={self.review_required}"
        )


class _Models:
    """Resolves model classes from either the live registry or a migration state."""

    def __init__(self, apps=None):
        self._apps = apps

    def get(self, app_label, model_name):
        if self._apps is not None:
            return self._apps.get_model(app_label, model_name)
        from django.apps import apps as global_apps

        return global_apps.get_model(app_label, model_name)


def backfill_default_branches(*, apps=None, using=None) -> BackfillResult:
    """§4.1 — ensure each tenant has exactly one default branch.

    Tenants with no Company are skipped and listed with a remediation note; a tenant
    that somehow has Branch rows without a Company is flagged REVIEW_REQUIRED rather
    than repaired by guesswork.
    """
    m = _Models(apps)
    Tenant = m.get("platform", "Tenant")
    Company = m.get("settings_app", "Company")
    Branch = m.get("settings_app", "Branch")

    result = BackfillResult("default_branch_per_tenant")
    tenants = Tenant.objects.all()
    if using:
        tenants = tenants.using(using)

    for tenant in tenants:
        result.total += 1
        branches = Branch.objects.filter(tenant_id=tenant.pk, deleted_at__isnull=True)
        if using:
            branches = branches.using(using)

        companies = Company.objects.filter(tenant_id=tenant.pk, deleted_at__isnull=True)
        if using:
            companies = companies.using(using)
        company = companies.order_by("created_at").first()

        if company is None:
            result.skipped += 1
            if branches.exists():
                result.review_required += 1
                result.details.append(
                    f"{tenant.slug}: REVIEW_REQUIRED — Branch rows exist but the tenant has no "
                    f"Company; reconcile ownership before re-running"
                )
            else:
                result.details.append(
                    f"{tenant.slug}: skipped — no Company; remediation: create a Company first"
                )
            continue

        defaults = list(branches.filter(is_default=True))
        if len(defaults) == 1:
            result.resolved += 1
            continue
        if len(defaults) > 1:
            # Keep the oldest, clear the rest: deterministic, not a guess about intent.
            keeper = sorted(defaults, key=lambda b: (b.created_at, str(b.pk)))[0]
            branches.filter(is_default=True).exclude(pk=keeper.pk).update(is_default=False)
            result.ambiguous += 1
            result.details.append(
                f"{tenant.slug}: had {len(defaults)} default branches; kept the oldest ({keeper.code})"
            )
            continue

        candidate = branches.filter(is_active=True).order_by("created_at", "id").first()
        if candidate is None:
            candidate = branches.order_by("created_at", "id").first()
            if candidate is not None:
                result.details.append(
                    f"{tenant.slug}: no active branch; marked inactive branch {candidate.code} as default"
                )
        if candidate is not None:
            candidate.is_default = True
            candidate.save(update_fields=["is_default", "updated_at"])
            result.resolved += 1
            continue

        # No branch at all: create the tenant's Main Branch against its oldest company.
        code = "MAIN"
        suffix = 0
        while branches.filter(code=code).exists():
            suffix += 1
            code = f"MAIN-{suffix}"
        Branch.objects.create(
            tenant_id=tenant.pk,
            company_id=company.pk,
            name="Main Branch",
            code=code,
            is_default=True,
            is_active=True,
        )
        result.resolved += 1
        result.details.append(f"{tenant.slug}: created default branch {code}")

    return result


def backfill_stock_locations(*, apps=None, using=None, include_transit=True) -> BackfillResult:
    """§4.2 — every warehouse gets the standard locations and exactly one default."""
    m = _Models(apps)
    Warehouse = m.get("inventory", "Warehouse")
    StockLocation = m.get("organization", "StockLocation")

    result = BackfillResult("stock_locations")
    warehouses = Warehouse.objects.filter(deleted_at__isnull=True)
    if using:
        warehouses = warehouses.using(using)

    specs = list(DEFAULT_LOCATION_SPECS)
    if include_transit:
        specs.append(TRANSIT_LOCATION)

    for warehouse in warehouses.iterator(chunk_size=500):
        result.total += 1
        created_default = None
        for code, name, location_type, is_sellable, is_default, sort_order in specs:
            existing = StockLocation.objects.filter(
                warehouse_id=warehouse.pk, code=code, deleted_at__isnull=True
            ).first()
            if existing is None:
                existing = StockLocation.objects.create(
                    tenant_id=warehouse.tenant_id,
                    warehouse_id=warehouse.pk,
                    code=code,
                    name=name,
                    location_type=location_type,
                    is_sellable=is_sellable,
                    is_default=False,
                    sort_order=sort_order,
                )
            if is_default:
                created_default = existing

        current_default = StockLocation.objects.filter(
            warehouse_id=warehouse.pk, is_default=True, deleted_at__isnull=True
        ).first()
        if current_default is None and created_default is not None:
            created_default.is_default = True
            created_default.save(update_fields=["is_default", "updated_at"])
            current_default = created_default

        if current_default is None:
            result.unresolved += 1
            result.details.append(f"warehouse {warehouse.code}: could not establish a default location")
        else:
            result.resolved += 1

    return result


def backfill_user_branch_access(*, apps=None, using=None) -> BackfillResult:
    """§4.3 — derive branch access from the legacy ``User.branch``.

    Users with no legacy branch get nothing (they keep working through the legacy
    fallback until an admin grants access). ``SchoolCampusAccess`` is deliberately
    **not** read: School authorisation keeps its own table, and copying it would
    silently grant retail branch access.
    """
    m = _Models(apps)
    User = m.get("authentication", "User")
    Permission = m.get("authentication", "Permission")
    Branch = m.get("settings_app", "Branch")
    UserBranchAccess = m.get("organization", "UserBranchAccess")
    BranchAccessProfile = m.get("organization", "BranchAccessProfile")

    result = BackfillResult("user_branch_access")

    profile_cache: dict = {}

    def profile_for(tenant_id, is_manager):
        key = (str(tenant_id), is_manager)
        if key in profile_cache:
            return profile_cache[key]
        code = "BRANCH_MANAGER" if is_manager else "BRANCH_STAFF"
        name = "Branch Manager" if is_manager else "Branch Staff"
        profile = BranchAccessProfile.objects.filter(
            tenant_id=tenant_id, code=code, deleted_at__isnull=True
        ).first()
        if profile is None:
            profile = BranchAccessProfile.objects.create(
                tenant_id=tenant_id,
                code=code,
                name=name,
                is_manager=is_manager,
                # Managers keep their full global permissions in the branch; staff are
                # narrowed to the list below. An empty list never means "everything".
                grants_all_permissions=is_manager,
                is_system=True,
                is_active=True,
            )
            if not is_manager:
                staff_codes = [
                    "dashboard.view",
                    "pos.access",
                    "products.view",
                    "inventory.view",
                    "sales.view",
                    "sales.create",
                    "customers.view",
                    "customers.create",
                ]
                profile.permissions.set(Permission.objects.filter(codename__in=staff_codes))
        profile_cache[key] = profile
        return profile

    users = User.objects.filter(deleted_at__isnull=True).exclude(branch_id=None)
    if using:
        users = users.using(using)

    for user in users.iterator(chunk_size=500):
        result.total += 1
        branch = Branch.objects.filter(pk=user.branch_id, deleted_at__isnull=True).first()
        if branch is None:
            result.skipped += 1
            result.details.append(f"user {user.username}: legacy branch no longer exists")
            continue

        tenant_id = branch.tenant_id or user.tenant_id
        if user.tenant_id and branch.tenant_id and str(user.tenant_id) != str(branch.tenant_id):
            result.review_required += 1
            result.details.append(
                f"user {user.username}: REVIEW_REQUIRED — user tenant {user.tenant_id} "
                f"differs from branch tenant {branch.tenant_id}; not backfilled"
            )
            continue

        if UserBranchAccess.objects.filter(
            user_id=user.pk, branch_id=branch.pk, deleted_at__isnull=True
        ).exists():
            result.resolved += 1
            continue

        role_slug = None
        if user.role_id:
            Role = m.get("authentication", "Role")
            role_slug = (
                Role.objects.filter(pk=user.role_id).values_list("slug", flat=True).first()
            )
        is_manager = role_slug in MANAGER_ROLE_SLUGS

        has_default = UserBranchAccess.objects.filter(
            user_id=user.pk, is_default=True, deleted_at__isnull=True
        ).exists()

        UserBranchAccess.objects.create(
            tenant_id=tenant_id,
            user_id=user.pk,
            branch_id=branch.pk,
            access_profile_id=profile_for(tenant_id, is_manager).pk if tenant_id else None,
            is_default=not has_default,
            status="ACTIVE",
            notes="Backfilled from legacy User.branch",
        )
        result.resolved += 1

    return result


def backfill_ledger_branch(*, apps=None, using=None) -> BackfillResult:
    """Migration plan §4.4 — ``StockMovement.branch``/``InventoryTransaction.branch``.

    A pure FK dereference: ``Warehouse.branch`` is already ``NOT NULL``, so every
    historical row resolves deterministically. Nothing is guessed.
    """
    m = _Models(apps)
    StockMovement = m.get("inventory", "StockMovement")
    InventoryTransaction = m.get("inventory", "InventoryTransaction")

    result = BackfillResult("ledger_branch")

    movements = StockMovement.objects.filter(branch__isnull=True)
    if using:
        movements = movements.using(using)
    total_movements = movements.count()
    updated_movements = 0
    # Chunked to avoid holding a huge queryset; UPDATE ... FROM warehouse in one pass
    # per warehouse keeps this to (number of distinct warehouses) queries, not one per row.
    warehouse_ids = list(
        movements.order_by().values_list("warehouse_id", flat=True).distinct()
    )
    Warehouse = m.get("inventory", "Warehouse")
    warehouses = Warehouse.objects.filter(pk__in=warehouse_ids)
    if using:
        warehouses = warehouses.using(using)
    branch_by_warehouse = dict(warehouses.values_list("pk", "branch_id"))
    for warehouse_id, branch_id in branch_by_warehouse.items():
        if not branch_id:
            continue
        updated_movements += movements.filter(warehouse_id=warehouse_id).update(
            branch_id=branch_id
        )

    transactions = InventoryTransaction.objects.filter(branch__isnull=True).select_related(
        "inventory"
    )
    if using:
        transactions = transactions.using(using)
    total_transactions = transactions.count()
    updated_transactions = 0
    Inventory = m.get("inventory", "Inventory")
    inv_qs = Inventory.objects.all()
    if using:
        inv_qs = inv_qs.using(using)
    warehouse_by_inventory = dict(inv_qs.values_list("pk", "warehouse_id"))
    for inventory_id, warehouse_id in warehouse_by_inventory.items():
        branch_id = branch_by_warehouse.get(warehouse_id)
        if branch_id is None and warehouse_id:
            wh = Warehouse.objects.filter(pk=warehouse_id).values_list("branch_id", flat=True).first()
            branch_id = wh
        if not branch_id:
            continue
        updated_transactions += InventoryTransaction.objects.filter(
            branch__isnull=True, inventory_id=inventory_id
        ).update(branch_id=branch_id)

    result.total = total_movements + total_transactions
    result.resolved = updated_movements + updated_transactions
    result.unresolved = result.total - result.resolved
    if result.unresolved:
        result.details.append(
            f"{result.unresolved} ledger rows point at a warehouse with no branch "
            "(should not happen — Warehouse.branch is NOT NULL) or a deleted warehouse"
        )
    return result


def backfill_pos_terminals(*, apps=None, using=None) -> BackfillResult:
    """§4.5 — one default terminal + register for every branch that has POS history.

    A branch qualifies when it has at least one ``CashierSession`` or ``Invoice``.
    The terminal sells from the branch's existing default warehouse (the warehouse the
    legacy sale path already used), so stock behaviour is unchanged. The register's
    ``cash_account`` stays NULL: it is a real accounting choice, never derived.

    At most one *open* session per terminal can exist (DB constraint). A branch that had
    several concurrently open sessions gets the oldest attached and the rest are reported
    as ``review_required`` rather than force-fitted.
    """
    m = _Models(apps)
    Branch = m.get("settings_app", "Branch")
    Warehouse = m.get("inventory", "Warehouse")
    StockLocation = m.get("organization", "StockLocation")
    PosTerminal = m.get("organization", "PosTerminal")
    CashRegister = m.get("organization", "CashRegister")
    CashierSession = m.get("sales", "CashierSession")
    Invoice = m.get("sales", "Invoice")

    result = BackfillResult("pos_terminals")

    def _qs(model):
        qs = model.objects.all()
        return qs.using(using) if using else qs

    branch_ids = set(
        _qs(CashierSession).filter(deleted_at__isnull=True).values_list("branch_id", flat=True)
    ) | set(_qs(Invoice).filter(deleted_at__isnull=True).values_list("branch_id", flat=True))

    for branch in _qs(Branch).filter(pk__in=branch_ids, deleted_at__isnull=True):
        result.total += 1
        warehouse = (
            _qs(Warehouse).filter(branch_id=branch.pk, is_default=True, deleted_at__isnull=True).first()
            or _qs(Warehouse).filter(branch_id=branch.pk, deleted_at__isnull=True).first()
        )
        location = None
        if warehouse is not None:
            location = (
                _qs(StockLocation)
                .filter(warehouse_id=warehouse.pk, is_default=True, deleted_at__isnull=True)
                .first()
            )

        register = _qs(CashRegister).filter(
            branch_id=branch.pk, code="REG-1", deleted_at__isnull=True
        ).first()
        if register is None:
            register = CashRegister.objects.create(
                tenant_id=branch.tenant_id,
                branch_id=branch.pk,
                code="REG-1",
                name="Main Register",
                status="ACTIVE",
            )
        terminal = _qs(PosTerminal).filter(
            branch_id=branch.pk, code="POS-1", deleted_at__isnull=True
        ).first()
        if terminal is None:
            terminal = PosTerminal.objects.create(
                tenant_id=branch.tenant_id,
                branch_id=branch.pk,
                code="POS-1",
                name="Main Terminal",
                default_warehouse_id=warehouse.pk if warehouse else None,
                default_location_id=location.pk if location else None,
                default_cash_register_id=register.pk,
                status="ACTIVE",
            )

        sessions = _qs(CashierSession).filter(
            branch_id=branch.pk, terminal__isnull=True, deleted_at__isnull=True
        )
        common = {
            "register_id": register.pk,
            "warehouse_id": warehouse.pk if warehouse else None,
            "location_id": location.pk if location else None,
        }
        sessions.exclude(status="open").update(terminal_id=terminal.pk, **common)

        open_sessions = list(sessions.filter(status="open").order_by("opened_at"))
        terminal_taken = _qs(CashierSession).filter(
            terminal_id=terminal.pk, status="open", deleted_at__isnull=True
        ).exists()
        if open_sessions and not terminal_taken:
            first = open_sessions.pop(0)
            _qs(CashierSession).filter(pk=first.pk).update(terminal_id=terminal.pk, **common)
        if open_sessions:
            result.review_required += len(open_sessions)
            result.details.append(
                f"branch {branch.code}: {len(open_sessions)} extra open session(s) left without a "
                "terminal (one open shift per terminal); close them or assign terminals"
            )
        result.resolved += 1
    return result


def backfill_journal_line_branch(*, apps=None, using=None) -> BackfillResult:
    """§4.6 — ``JournalLine.branch = entry.branch`` where the entry has one.

    ``JournalEntry.branch`` itself is never inferred. Entries with no branch stay
    *Unassigned*; that is an accepted, reported outcome, not a failure.
    """
    m = _Models(apps)
    JournalEntry = m.get("finance", "JournalEntry")
    JournalLine = m.get("finance", "JournalLine")

    result = BackfillResult("journal_line_branch")

    def _qs(model):
        qs = model.objects.all()
        return qs.using(using) if using else qs

    entries = _qs(JournalEntry).filter(branch__isnull=False)
    branch_ids = list(entries.order_by().values_list("branch_id", flat=True).distinct())
    pending = _qs(JournalLine).filter(branch__isnull=True, entry__branch__isnull=False)
    result.total = pending.count()
    for branch_id in branch_ids:
        result.resolved += (
            _qs(JournalLine)
            .filter(branch__isnull=True, entry__branch_id=branch_id)
            .update(branch_id=branch_id)
        )
    result.unresolved = result.total - result.resolved
    result.skipped = _qs(JournalLine).filter(entry__branch__isnull=True).count()
    if result.skipped:
        result.details.append(
            f"{result.skipped} lines belong to entries with no branch (reported as Unassigned)"
        )
    return result


def run_all(*, apps=None, using=None) -> list[BackfillResult]:
    return [
        backfill_default_branches(apps=apps, using=using),
        backfill_stock_locations(apps=apps, using=using),
        backfill_user_branch_access(apps=apps, using=using),
    ]
