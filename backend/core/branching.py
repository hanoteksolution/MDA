"""Request-scoped branch context and branch-aware authorisation.

This is the single place the ERP decides "which branches may this actor touch right
now?". Modules must not re-implement branch filtering; they call
:func:`resolve_branch_scope` / :func:`apply_branch_scope` instead.

Rules that must not be weakened:

* The requested branch (``X-Branch-Id`` header, query param, or body field) is
  **untrusted input**. It is intersected with what the user actually holds; it can
  only ever narrow the scope, never widen it. Changing the id in a URL, body, query
  string or header therefore cannot bypass authorisation.
* A branch access profile can only **narrow** a user's global permissions. Branch
  access is never a privilege-escalation path.
* Fail closed: an unknown, malformed or unauthorised branch is rejected, never
  silently ignored and never widened to "everything".
* Fail safe for migration: a user who has no :class:`UserBranchAccess` rows yet
  falls back to their legacy ``User.branch``, so backfilling cannot lock anyone out.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Iterable, Optional

from rest_framework import permissions
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.tenancy import is_platform_unscoped_actor, resolve_acting_tenant

BRANCH_HEADER = "X-Branch-Id"
BRANCH_HEADER_META = "HTTP_X_BRANCH_ID"
BRANCH_QUERY_PARAM = "branch_id"
ALL_BRANCHES = "all"

_REQUEST_CACHE_ATTR = "_mda_branch_scope_cache"


@dataclass(frozen=True)
class BranchScope:
    """The branches an actor may act in for the current request.

    ``branch_ids`` is already intersected with the actor's real access, so callers
    can filter on it directly without re-checking authorisation.
    """

    branch_ids: tuple = ()
    explicit: bool = False
    requested_all: bool = False
    unscoped: bool = False
    tenant_id: Optional[object] = None
    permission: Optional[str] = None
    _branch_id_strings: frozenset = field(default_factory=frozenset, repr=False, compare=False)

    @property
    def is_all(self) -> bool:
        """True when the scope covers every accessible branch (no single selection)."""
        return not self.explicit

    @property
    def is_empty(self) -> bool:
        return not self.unscoped and not self.branch_ids

    @property
    def branch_id(self):
        """The single selected branch, or None when the scope is not a single branch."""
        if self.explicit and len(self.branch_ids) == 1:
            return self.branch_ids[0]
        return None

    def allows(self, branch_id) -> bool:
        if branch_id is None:
            return False
        if self.unscoped:
            return True
        return str(branch_id) in self._branch_id_strings

    def require_single(self, action: str = "this operation"):
        """Return the one branch this request acts on, or refuse an ambiguous scope.

        POS and every stock-mutating path go through here: writing to "all branches"
        is meaningless and must never be guessed.
        """
        if self.requested_all:
            raise ValidationError(
                {
                    "branch_id": (
                        f"Select a single branch for {action}. "
                        "'all' is not a valid branch for this request."
                    )
                }
            )
        if len(self.branch_ids) == 1:
            return self.branch_ids[0]
        if not self.branch_ids:
            raise PermissionDenied(f"No branch access for {action}.")
        raise ValidationError(
            {"branch_id": f"Select a single branch for {action}."}
        )

    def filter(self, queryset, *, field_name: str = "branch_id"):
        """Narrow a queryset to this scope. Unscoped actors are not filtered."""
        if self.unscoped:
            return queryset
        if not self.branch_ids:
            return queryset.none()
        return queryset.filter(**{f"{field_name}__in": list(self.branch_ids)})


def _as_uuid(value):
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return None


def _tenant_pk(tenant):
    if tenant is None:
        return None
    return getattr(tenant, "pk", None) or getattr(tenant, "id", None) or tenant


def _make_scope(branch_ids: Iterable, **kwargs) -> BranchScope:
    ids = tuple(branch_ids)
    return BranchScope(
        branch_ids=ids,
        _branch_id_strings=frozenset(str(i) for i in ids),
        **kwargs,
    )


# --------------------------------------------------------------------------- #
# Accessible branches
# --------------------------------------------------------------------------- #

def accessible_branches(user, *, tenant=None, request=None, permission: str | None = None):
    """Branch queryset the user may act in, optionally restricted to a permission.

    Elevated admins get every branch in the acting tenant (matching how they already
    bypass tenant scope). Everyone else gets their effective ``UserBranchAccess``
    rows, falling back to the legacy ``User.branch`` while they have none.
    """
    from apps.settings_app.models import Branch

    if user is None or not getattr(user, "is_authenticated", False):
        return Branch.objects.none()

    tenant = tenant if tenant is not None else resolve_acting_tenant(request=request, user=user)
    tenant_id = _tenant_pk(tenant)

    qs = Branch.active_objects().select_related("company")
    if tenant_id is not None:
        qs = qs.filter(tenant_id=tenant_id)

    if is_platform_unscoped_actor(user):
        return qs

    access_branch_ids = _effective_access_branch_ids(user, tenant_id=tenant_id)
    if access_branch_ids is None:
        legacy_branch_id = getattr(user, "branch_id", None)
        if not legacy_branch_id:
            return Branch.objects.none()
        qs = qs.filter(pk=legacy_branch_id)
    else:
        qs = qs.filter(pk__in=access_branch_ids)

    if permission:
        allowed = [b.pk for b in qs if has_branch_permission(user, permission, b)]
        qs = qs.filter(pk__in=allowed)
    return qs


def _effective_access_branch_ids(user, *, tenant_id=None):
    """Branch ids from effective UserBranchAccess rows, or None when the user has none.

    ``None`` (rather than an empty list) is what triggers the legacy fallback: it
    distinguishes "not migrated yet" from "explicitly has no branch access".
    """
    from apps.organization.models import UserBranchAccess

    rows = UserBranchAccess.objects.filter(user_id=user.pk, deleted_at__isnull=True)
    if tenant_id is not None:
        rows = rows.filter(branch__tenant_id=tenant_id)
    if not rows.exists():
        return None
    return list(
        rows.filter(UserBranchAccess.effective_filter())
        .filter(branch__deleted_at__isnull=True, branch__is_active=True)
        .values_list("branch_id", flat=True)
    )


def default_branch_for(user, *, tenant=None, request=None):
    """The branch to select when the client did not ask for one."""
    from apps.organization.models import UserBranchAccess

    if user is None or not getattr(user, "is_authenticated", False):
        return None
    tenant_id = _tenant_pk(tenant if tenant is not None else resolve_acting_tenant(request=request, user=user))
    row = (
        UserBranchAccess.objects.filter(user_id=user.pk, is_default=True, deleted_at__isnull=True)
        .filter(UserBranchAccess.effective_filter())
        .order_by("created_at")
        .first()
    )
    if row is not None:
        return row.branch_id
    legacy = getattr(user, "branch_id", None)
    if legacy:
        return legacy
    branches = accessible_branches(user, tenant=tenant, request=request)
    first = branches.filter(is_default=True).values_list("pk", flat=True).first()
    if first:
        return first
    return branches.values_list("pk", flat=True).first()


# --------------------------------------------------------------------------- #
# Branch-aware permissions
# --------------------------------------------------------------------------- #

def branch_permissions(user, branch) -> set[str]:
    """Effective permission codenames for this user *inside* this branch."""
    if user is None or not getattr(user, "is_authenticated", False):
        return set()
    global_codes = set(user.get_permissions())
    if is_platform_unscoped_actor(user):
        return global_codes

    branch_id = getattr(branch, "pk", branch)
    from apps.organization.models import UserBranchAccess

    row = (
        UserBranchAccess.objects.filter(
            user_id=user.pk, branch_id=branch_id, deleted_at__isnull=True
        )
        .filter(UserBranchAccess.effective_filter())
        .select_related("access_profile")
        .first()
    )
    if row is None:
        # Legacy fallback: only while the user has no access rows at all.
        if _effective_access_branch_ids(user) is None and str(getattr(user, "branch_id", "")) == str(branch_id):
            return global_codes
        return set()
    profile = row.access_profile
    if profile is None or not profile.is_active or profile.grants_all_permissions:
        return global_codes
    # A profile narrows; it can never add a permission the user does not hold.
    # An empty profile therefore means "nothing here", never "everything".
    return global_codes & profile.permission_codenames()


def has_branch_permission(user, codename: str, branch) -> bool:
    """True when the user holds ``codename`` *and* it applies in this branch."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if is_platform_unscoped_actor(user):
        return True
    if not user.has_permission(codename):
        return False
    return codename in branch_permissions(user, branch)


def is_branch_manager(user, branch) -> bool:
    from apps.organization.models import UserBranchAccess

    if is_platform_unscoped_actor(user):
        return True
    branch_id = getattr(branch, "pk", branch)
    row = (
        UserBranchAccess.objects.filter(
            user_id=user.pk, branch_id=branch_id, deleted_at__isnull=True
        )
        .filter(UserBranchAccess.effective_filter())
        .select_related("access_profile")
        .first()
    )
    if row is None:
        return False
    if row.access_profile_id and row.access_profile.is_manager:
        return True
    from apps.settings_app.models import Branch

    return Branch.objects.filter(pk=branch_id, manager_id=user.pk).exists()


# --------------------------------------------------------------------------- #
# Scope resolution
# --------------------------------------------------------------------------- #

def _requested_branch(request, explicit_value=None):
    if explicit_value is not None:
        return str(explicit_value).strip()
    if request is None:
        return None
    header = request.META.get(BRANCH_HEADER_META) or ""
    if not header and hasattr(request, "headers"):
        header = request.headers.get(BRANCH_HEADER) or ""
    header = header.strip()
    if header:
        return header
    params = getattr(request, "query_params", None) or getattr(request, "GET", None)
    if params:
        value = (params.get(BRANCH_QUERY_PARAM) or "").strip()
        if value:
            return value
    return None


def resolve_branch_scope(
    *,
    request=None,
    user=None,
    requested=None,
    permission: str | None = None,
    allow_all: bool = True,
    use_default: bool = False,
) -> BranchScope:
    """Resolve the branch scope for this actor, fail-closed.

    ``permission`` restricts the scope to branches where that codename actually
    applies, which is how a user can legitimately hold different rights per branch.
    ``allow_all=False`` refuses the literal ``all`` selector (POS, stock mutations).
    ``use_default`` selects the user's default branch when the client sent nothing.
    """
    if user is None and request is not None:
        user = getattr(request, "user", None)

    if user is None or not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required for branch access.")

    tenant = resolve_acting_tenant(request=request, user=user)
    tenant_id = _tenant_pk(tenant)
    branches = accessible_branches(user, tenant=tenant, request=request, permission=permission)
    accessible_ids = list(branches.values_list("pk", flat=True))

    unscoped = is_platform_unscoped_actor(user) and tenant_id is None
    raw = _requested_branch(request, requested)

    if raw is None or raw == "":
        if use_default:
            default_id = default_branch_for(user, tenant=tenant, request=request)
            if default_id is not None and str(default_id) in {str(i) for i in accessible_ids}:
                return _make_scope(
                    [default_id],
                    explicit=True,
                    tenant_id=tenant_id,
                    permission=permission,
                    unscoped=False,
                )
        return _make_scope(
            accessible_ids,
            explicit=False,
            requested_all=False,
            unscoped=unscoped,
            tenant_id=tenant_id,
            permission=permission,
        )

    if raw.lower() == ALL_BRANCHES:
        if not allow_all:
            raise ValidationError(
                {"branch_id": "Select a single branch. 'all' is not valid for this request."}
            )
        return _make_scope(
            accessible_ids,
            explicit=False,
            requested_all=True,
            unscoped=unscoped,
            tenant_id=tenant_id,
            permission=permission,
        )

    branch_uuid = _as_uuid(raw)
    if branch_uuid is None:
        raise ValidationError({"branch_id": "Invalid branch identifier."})

    if str(branch_uuid) not in {str(i) for i in accessible_ids}:
        # Never distinguish "does not exist" from "not yours": no tenant probing.
        raise PermissionDenied("You do not have access to this branch.")

    return _make_scope(
        [branch_uuid],
        explicit=True,
        tenant_id=tenant_id,
        permission=permission,
        unscoped=False,
    )


def get_branch_scope(request, **kwargs) -> BranchScope:
    """Per-request memoised :func:`resolve_branch_scope` (same kwargs = same scope)."""
    cache = getattr(request, _REQUEST_CACHE_ATTR, None)
    if cache is None:
        cache = {}
        setattr(request, _REQUEST_CACHE_ATTR, cache)
    key = (
        kwargs.get("permission"),
        kwargs.get("allow_all", True),
        kwargs.get("use_default", False),
        str(kwargs.get("requested")) if kwargs.get("requested") is not None else None,
    )
    if key not in cache:
        cache[key] = resolve_branch_scope(request=request, **kwargs)
    return cache[key]


def apply_branch_scope(
    queryset,
    *,
    scope: BranchScope | None = None,
    request=None,
    user=None,
    field_name: str = "branch_id",
    permission: str | None = None,
):
    """Filter a queryset by the acting branch scope. The one entry point modules use."""
    if scope is None:
        scope = (
            get_branch_scope(request, permission=permission)
            if request is not None
            else resolve_branch_scope(user=user, permission=permission)
        )
    return scope.filter(queryset, field_name=field_name)


# --------------------------------------------------------------------------- #
# Cross-tenant integrity
# --------------------------------------------------------------------------- #

def assert_same_tenant(*objects, label: str = "record"):
    """Refuse to link rows that belong to different tenants.

    Used for the warehouse rule: a Warehouse and its Branch must share a tenant, and
    neither may point across a tenant boundary.
    """
    tenant_ids = set()
    for obj in objects:
        if obj is None:
            continue
        tenant_id = getattr(obj, "tenant_id", None)
        if tenant_id is not None:
            tenant_ids.add(str(tenant_id))
    if len(tenant_ids) > 1:
        raise ValidationError(
            {"tenant": f"Cross-tenant reference rejected for {label}."}
        )
    return True


# --------------------------------------------------------------------------- #
# DRF permission classes
# --------------------------------------------------------------------------- #

def HasBranchPermission(codename: str, *, allow_all: bool = True):
    """DRF permission: holds ``codename`` in at least one branch of the resolved scope.

    The resolved scope is attached to ``request.branch_scope`` so the view does not
    resolve it twice, and the view still filters by it — this class authorises, the
    scope filters.
    """

    class _HasBranchPermission(permissions.BasePermission):
        message = "You do not have this permission in the selected branch."

        def has_permission(self, request, view):
            user = getattr(request, "user", None)
            if not user or not user.is_authenticated:
                return False
            if not user.has_permission(codename):
                return False
            scope = get_branch_scope(request, permission=codename, allow_all=allow_all)
            request.branch_scope = scope
            return scope.unscoped or bool(scope.branch_ids)

    safe = codename.replace(".", "_")
    _HasBranchPermission.__name__ = f"HasBranchPermission_{safe}"
    _HasBranchPermission.__qualname__ = _HasBranchPermission.__name__
    return _HasBranchPermission
