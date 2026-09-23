"""Multi-branch fixtures for the Branch Phase 2 suites.

Builds the worked example from the phase brief: one tenant, three branches, and a
user who holds different rights in each of them.

    Ahmed  Hodan   -> POS, Sales, Inventory
           Bakaaro -> Inventory view only
           Main    -> no access at all
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.contrib.auth import get_user_model

from decimal import Decimal

from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Permission, Role
from apps.inventory.models import Inventory, Warehouse
from apps.organization.models import BranchAccessProfile, UserBranchAccess
from apps.organization.services import BranchAccessService, StockLocationService
from apps.platform.models import Tenant
from apps.platform.services.module_service import sync_tenant_modules
from apps.products.models import Category, Product, Unit
from apps.settings_app.models import Branch, Company

User = get_user_model()

POS_SALES_CODES = [
    "dashboard.view",
    "pos.access",
    "sales.view",
    "sales.create",
    "inventory.view",
    "inventory.adjust",
]
VIEW_ONLY_CODES = ["inventory.view"]


@dataclass
class BranchContext:
    tenant: Tenant
    company: Company
    branches: dict = field(default_factory=dict)
    warehouses: dict = field(default_factory=dict)
    users: dict = field(default_factory=dict)
    profiles: dict = field(default_factory=dict)

    def branch(self, code: str) -> Branch:
        return self.branches[code]

    def warehouse(self, code: str) -> Warehouse:
        return self.warehouses[code]

    def inventory(self, product, branch_code: str) -> Inventory:
        return Inventory.objects.get(product=product, warehouse=self.warehouse(branch_code))


def make_profile(*, tenant, code, name, codenames, is_manager=False):
    profile = BranchAccessProfile.objects.create(
        tenant=tenant, code=code, name=name, is_manager=is_manager
    )
    profile.permissions.set(Permission.objects.filter(codename__in=codenames))
    return profile


def build_branch_tenant(
    *,
    slug: str = "multi-branch",
    branch_codes: tuple[str, ...] = ("MAIN", "HODAN", "BAKAARO"),
    # NB: "products" is NOT a valid module code — passing it raises ModuleDependencyError.
    # (That is the root cause of the pre-existing test_tenant_isolation_api baseline errors.)
    modules: tuple[str, ...] = ("pos", "inventory", "sales", "purchases"),
    with_locations: bool = True,
) -> BranchContext:
    """One tenant, several branches, one warehouse each, default locations seeded."""
    bootstrap_roles_and_permissions()
    tenant = Tenant.objects.create(
        name=f"{slug.title()} Group", slug=slug, status=Tenant.STATUS_ACTIVE
    )
    sync_tenant_modules(tenant=tenant, enabled_codes=list(modules))
    company = Company.objects.create(name=f"{slug.title()} Group", tenant=tenant)

    ctx = BranchContext(tenant=tenant, company=company)
    for index, code in enumerate(branch_codes):
        branch = Branch.objects.create(
            tenant=tenant,
            company=company,
            name=code.title(),
            code=code,
            is_default=(index == 0),
        )
        warehouse = Warehouse.objects.create(
            tenant=tenant,
            branch=branch,
            name=f"{code.title()} WH",
            code=f"WH-{code}",
            is_default=True,
        )
        ctx.branches[code] = branch
        ctx.warehouses[code] = warehouse
        if with_locations:
            StockLocationService.ensure_default_locations(warehouse=warehouse)
    return ctx


def add_user(
    ctx: BranchContext,
    *,
    username: str,
    role_slug: str = "admin",
    legacy_branch: str | None = None,
    branches: tuple[str, ...] | list[str] | None = None,
) -> User:
    """Create a user. ``branches`` grants unprofiled (full-permission) access to each.

    Branch access is always explicit in these fixtures: a user with no grant and no
    ``legacy_branch`` genuinely has access to nothing, which is what the services
    enforce.
    """
    user = User.objects.create_user(
        username=username,
        password="pass12345",
        tenant=ctx.tenant,
        branch=ctx.branches[legacy_branch] if legacy_branch else None,
        role=Role.objects.get(slug=role_slug),
    )
    ctx.users[username] = user
    for index, code in enumerate(branches or ()):
        grant(ctx, user=user, branch_code=code, is_default=(index == 0))
    return user


def add_owner(ctx: BranchContext, *, username: str, role_slug: str = "admin") -> User:
    """An admin with access to every branch in the fixture."""
    return add_user(ctx, username=username, role_slug=role_slug, branches=tuple(ctx.branches))


def grant(
    ctx: BranchContext,
    *,
    user,
    branch_code: str,
    profile=None,
    is_default: bool = False,
    starts_on=None,
    ends_on=None,
    status: str = UserBranchAccess.STATUS_ACTIVE,
) -> UserBranchAccess:
    """Grant branch access directly (bypassing the actor permission check)."""
    access = UserBranchAccess.objects.create(
        tenant=ctx.tenant,
        user=user,
        branch=ctx.branches[branch_code],
        access_profile=profile,
        is_default=is_default,
        starts_on=starts_on,
        ends_on=ends_on,
        status=status,
    )
    if is_default:
        BranchAccessService.set_default(access=access)
    return access


def build_ahmed(ctx: BranchContext):
    """The worked example: different permissions per branch, no access to Main."""
    ahmed = add_user(ctx, username="ahmed", role_slug="admin")
    pos_profile = make_profile(
        tenant=ctx.tenant, code="POS_SALES", name="POS & Sales", codenames=POS_SALES_CODES
    )
    view_profile = make_profile(
        tenant=ctx.tenant, code="VIEW_ONLY", name="Inventory Viewer", codenames=VIEW_ONLY_CODES
    )
    ctx.profiles["POS_SALES"] = pos_profile
    ctx.profiles["VIEW_ONLY"] = view_profile
    grant(ctx, user=ahmed, branch_code="HODAN", profile=pos_profile, is_default=True)
    grant(ctx, user=ahmed, branch_code="BAKAARO", profile=view_profile)
    # No UserBranchAccess row for MAIN: no access.
    return ahmed


def add_product(
    ctx: BranchContext,
    *,
    sku: str,
    name: str | None = None,
    minimum_stock: int = 5,
    cost_price=Decimal("1"),
    selling_price=Decimal("10"),
) -> Product:
    """One shared category/unit per tenant, reused across products — Phase 3 tests
    care about inventory quantities, not catalog structure."""
    category, _ = Category.objects.get_or_create(
        tenant=ctx.tenant, name="General", defaults={"tenant": ctx.tenant}
    )
    unit, _ = Unit.objects.get_or_create(
        tenant=ctx.tenant, abbreviation="pc", defaults={"tenant": ctx.tenant, "name": "Piece"}
    )
    return Product.objects.create(
        tenant=ctx.tenant,
        sku=sku,
        name=name or sku,
        category=category,
        unit=unit,
        cost_price=cost_price,
        selling_price=selling_price,
        minimum_stock=minimum_stock,
    )


def set_inventory(
    ctx: BranchContext,
    *,
    product: Product,
    branch_code: str,
    quantity=Decimal("0"),
    reserved=Decimal("0"),
) -> Inventory:
    """Create or overwrite the (product, warehouse) balance directly — a test fixture,
    not a mutation path; production code never writes Inventory.quantity like this."""
    warehouse = ctx.warehouse(branch_code)
    inv, _ = Inventory.objects.update_or_create(
        product=product,
        warehouse=warehouse,
        defaults={
            "tenant": ctx.tenant,
            "quantity": Decimal(str(quantity)),
            "reserved_quantity": Decimal(str(reserved)),
        },
    )
    return inv
