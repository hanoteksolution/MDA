"""Branch-aware reports: single branch, several branches, or consolidated (Phase 6).

Every report returns the per-branch rows **and** a consolidated block that is computed by an
*independent* aggregate (no GROUP BY), plus ``reconciles`` — the hard gate B6-2 that
consolidated == Σ branches (+ the Unassigned bucket for P&L). Nothing here derives the
consolidated figure by summing the rows, so a bug in either path shows up as ``False``.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from rest_framework.exceptions import PermissionDenied, ValidationError

from core.branching import (
    BRANCH_HEADER,
    BRANCH_QUERY_PARAM,
    accessible_branches,
)

ZERO = Decimal("0")
REPORTS = ("sales", "stock-value", "profit-loss", "cash", "purchases", "inventory", "expenses", "transfers")


class ReportScopeError(ValidationError):
    pass


@dataclass(frozen=True)
class ReportScope:
    """Branches a report covers. ``mode``: single | multi | consolidated."""

    branch_ids: tuple
    mode: str
    tenant_id: object
    covers_all: bool  # caller sees every branch of the tenant (Unassigned finance data allowed)


def _uuid_list(raw: str) -> list:
    import uuid

    out = []
    for part in [p.strip() for p in raw.split(",") if p.strip()]:
        try:
            out.append(uuid.UUID(part))
        except ValueError:
            raise ReportScopeError({"branch_id": "Invalid branch identifier."})
    return out


def _tenant_branch_ids(request, user):
    from core.tenancy import resolve_acting_tenant
    from apps.settings_app.models import Branch

    tenant = resolve_acting_tenant(request=request, user=user)
    tenant_id = getattr(tenant, "pk", None)
    qs = Branch.active_objects()
    if tenant_id is not None:
        qs = qs.filter(tenant_id=tenant_id)
    return tenant_id, {str(pk) for pk in qs.values_list("pk", flat=True)}


def _raw_request(request):
    if request is None:
        return None
    raw = (request.query_params.get(BRANCH_QUERY_PARAM) or "").strip() if hasattr(
        request, "query_params"
    ) else ""
    return raw or (request.headers.get(BRANCH_HEADER) or "").strip() or None


def resolve_report_scope(*, request=None, user=None, requested=None) -> ReportScope:
    """Fail-closed scope for a report: an inaccessible branch is a 403, never an empty page.

    ``requested``: one id, a comma-separated list, ``"all"``/None (consolidated over every
    branch the caller may see with ``reports.view``).
    """
    user = user or getattr(request, "user", None)
    raw = str(requested).strip() if requested else _raw_request(request)
    tenant_id, tenant_all = _tenant_branch_ids(request, user)
    allowed = {
        str(pk)
        for pk in accessible_branches(user, request=request, permission="reports.view").values_list(
            "pk", flat=True
        )
    }
    if not raw or raw.lower() == "all":
        ids = sorted(allowed)
        mode = "consolidated"
    else:
        ids = [str(u) for u in _uuid_list(raw)]
        if not ids:
            raise ReportScopeError({"branch_id": "Invalid branch identifier."})
        if not set(ids) <= allowed:
            # Same answer for "not yours" and "does not exist": no tenant probing.
            raise PermissionDenied("You do not have access to this branch.")
        mode = "single" if len(ids) == 1 else "multi"
    return ReportScope(
        branch_ids=tuple(ids),
        mode=mode,
        tenant_id=tenant_id,
        covers_all=bool(tenant_all) and tenant_all <= allowed,
    )


def resolve_view_branch_id(request):
    """Single ``branch_id`` (or None = whole tenant) for the legacy single-branch services.

    Dashboards and the classic reports take one branch. No selection keeps today's default
    (the user's own branch). A named branch must be accessible (403 otherwise); ``all`` is
    only honoured for callers who can see every branch — otherwise 403, never a silent
    narrowing or widening.
    """
    user = request.user
    raw = _raw_request(request)
    if not raw:
        return getattr(getattr(user, "branch", None), "id", None)
    scope = resolve_report_scope(request=request, user=user, requested=raw)
    if raw.lower() == "all":
        if not scope.covers_all:
            raise PermissionDenied("Consolidated view needs access to every branch.")
        return None
    if scope.mode != "single":
        raise ReportScopeError({"branch_id": "Select a single branch for this view."})
    return scope.branch_ids[0]


# --------------------------------------------------------------------------- #
# Metrics. Each returns (grouped_by_branch, consolidated) from independent queries.
# --------------------------------------------------------------------------- #


def _dec(value) -> Decimal:
    return Decimal(str(value)) if value is not None else ZERO


def _agg(qs, field, **aggs):
    grouped = {}
    for row in qs.order_by().values(field).annotate(**aggs):
        grouped[row[field]] = {k: _dec(row[k]) for k in aggs}
    total = {k: _dec(v) for k, v in qs.aggregate(**aggs).items()}
    return grouped, total


def _date_filter(qs, field, date_from, date_to):
    if date_from:
        qs = qs.filter(**{f"{field}__gte": date_from})
    if date_to:
        qs = qs.filter(**{f"{field}__lte": date_to})
    return qs


def _sales(ids, date_from, date_to):
    from django.db.models import Count
    from apps.sales.models import Invoice

    qs = Invoice.active_objects().filter(branch_id__in=ids).exclude(
        status__in=[Invoice.STATUS_DRAFT, Invoice.STATUS_ON_HOLD, Invoice.STATUS_CANCELLED]
    )
    qs = _date_filter(qs, "issue_date", date_from, date_to)
    return _agg(
        qs, "branch_id", invoices=Count("id"), gross=Sum("total_amount"), refunded=Sum("amount_refunded")
    )


def _stock_value(ids, date_from, date_to):
    from apps.inventory.models import Inventory

    value = ExpressionWrapper(
        F("quantity") * F("product__cost_price"), output_field=DecimalField(max_digits=24, decimal_places=4)
    )
    qs = Inventory.objects.filter(warehouse__branch_id__in=ids, deleted_at__isnull=True).annotate(
        _branch=F("warehouse__branch_id")
    )
    return _agg(qs, "_branch", units=Sum("quantity"), value=Sum(value))


def _cash(ids, date_from, date_to):
    from apps.sales.models import CashierSession, Payment, SaleRefund

    pay = Payment.active_objects().filter(branch_id__in=ids, method=Payment.METHOD_CASH)
    pay = _date_filter(pay, "paid_at__date", date_from, date_to)
    ref = _date_filter(
        SaleRefund.active_objects().filter(branch_id__in=ids), "created_at__date", date_from, date_to
    )
    ses = _date_filter(
        CashierSession.active_objects().filter(branch_id__in=ids), "opened_at__date", date_from, date_to
    )
    g_pay, t_pay = _agg(pay, "branch_id", cash_received=Sum("amount"))
    g_ref, t_ref = _agg(ref, "branch_id", cash_refunded=Sum("total_amount"))
    g_ses, t_ses = _agg(
        ses, "branch_id", cash_in=Sum("cash_in"), cash_out=Sum("cash_out"), variance=Sum("cash_variance")
    )
    grouped = {}
    for bid in set(g_pay) | set(g_ref) | set(g_ses):
        grouped[bid] = {
            **g_pay.get(bid, {"cash_received": ZERO}),
            **g_ref.get(bid, {"cash_refunded": ZERO}),
            **g_ses.get(bid, {"cash_in": ZERO, "cash_out": ZERO, "variance": ZERO}),
        }
    return grouped, {**t_pay, **t_ref, **t_ses}


def _pnl(ids, date_from, date_to, *, include_unassigned):
    from django.db.models import Q
    from apps.finance.models import JournalEntry, JournalLine

    base = JournalLine.active_objects().filter(
        entry__status=JournalEntry.STATUS_POSTED,
        entry__deleted_at__isnull=True,
        account__account_type__in=["revenue", "expense"],
    )
    scope_q = Q(branch_id__in=ids)
    if include_unassigned:
        scope_q |= Q(branch__isnull=True)
    qs = _date_filter(base.filter(scope_q), "entry__entry_date", date_from, date_to)
    rev = Sum("credit", filter=Q(account__account_type="revenue")) - Sum(
        "debit", filter=Q(account__account_type="revenue")
    )
    exp = Sum("debit", filter=Q(account__account_type="expense")) - Sum(
        "credit", filter=Q(account__account_type="expense")
    )
    return _agg(qs, "branch_id", revenue=rev, expenses=exp)


def _purchases(ids, date_from, date_to):
    from django.db.models import Count, Q
    from apps.purchases.models import PurchaseOrder

    qs = PurchaseOrder.active_objects().filter(branch_id__in=ids).exclude(status=PurchaseOrder.STATUS_CANCELLED)
    qs = _date_filter(qs, "order_date", date_from, date_to)
    received = Q(status=PurchaseOrder.STATUS_RECEIVED)
    open_q = Q(status__in=[PurchaseOrder.STATUS_DRAFT, PurchaseOrder.STATUS_ORDERED])
    return _agg(
        qs, "branch_id", orders=Count("id"), ordered_total=Sum("total_amount"),
        received_orders=Count("id", filter=received), received_total=Sum("total_amount", filter=received),
        open_orders=Count("id", filter=open_q), open_total=Sum("total_amount", filter=open_q),
    )


def _inventory(ids, date_from, date_to):
    """Current stock health per branch (a snapshot: date filters do not apply)."""
    from django.db.models import Count, Q
    from apps.inventory.models import Inventory

    qs = Inventory.objects.filter(
        warehouse__branch_id__in=ids, deleted_at__isnull=True, warehouse__deleted_at__isnull=True,
        product__deleted_at__isnull=True,
    ).annotate(_branch=F("warehouse__branch_id"))
    low = Q(quantity__gt=0, quantity__lte=F("product__minimum_stock"))
    return _agg(
        qs, "_branch", stock_lines=Count("id"), units=Sum("quantity"), reserved=Sum("reserved_quantity"),
        low_stock=Count("id", filter=low), out_of_stock=Count("id", filter=Q(quantity__lte=0)),
    )


def _expenses(ids, date_from, date_to):
    from django.db.models import Count
    from apps.sales.models import Expense

    qs = _date_filter(Expense.active_objects().filter(branch_id__in=ids), "expense_date", date_from, date_to)
    return _agg(qs, "branch_id", entries=Count("id"), amount=Sum("amount"))


def _transfers(ids, date_from, date_to):
    """Transfer counts per branch. Outgoing = branch is the source; incoming = the destination."""
    from django.db.models import Count, Q
    from apps.inventory.models import BranchTransferRequest as T

    open_statuses = [T.STATUS_REQUESTED, T.STATUS_APPROVED, T.STATUS_RESERVED, T.STATUS_DISPATCHED,
                     T.STATUS_IN_TRANSIT, T.STATUS_RECEIVED]
    base = _date_filter(T.active_objects(), "created_at__date", date_from, date_to)
    aggs_out = {"outgoing": Count("id"), "outgoing_open": Count("id", filter=Q(status__in=open_statuses)),
                "awaiting_approval": Count("id", filter=Q(status=T.STATUS_REQUESTED))}
    aggs_in = {"incoming": Count("id"), "incoming_open": Count("id", filter=Q(status__in=open_statuses)),
               "in_transit": Count("id", filter=Q(status=T.STATUS_IN_TRANSIT))}
    g_out, t_out = _agg(base.filter(source_branch_id__in=ids), "source_branch_id", **aggs_out)
    g_in, t_in = _agg(base.filter(destination_branch_id__in=ids), "destination_branch_id", **aggs_in)
    zero_out, zero_in = {k: ZERO for k in aggs_out}, {k: ZERO for k in aggs_in}
    grouped = {bid: {**g_out.get(bid, zero_out), **g_in.get(bid, zero_in)} for bid in set(g_out) | set(g_in)}
    return grouped, {**t_out, **t_in}


def _derive(report, figures):
    f = dict(figures)
    if report == "sales":
        f["net"] = f.get("gross", ZERO) - f.get("refunded", ZERO)
    elif report == "profit-loss":
        f["net_profit"] = f.get("revenue", ZERO) - f.get("expenses", ZERO)
    elif report == "cash":
        f["net_cash"] = (
            f.get("cash_received", ZERO) - f.get("cash_refunded", ZERO)
            + f.get("cash_in", ZERO) - f.get("cash_out", ZERO)
        )
    return f


def _fl(figures):
    return {k: float(v) for k, v in figures.items()}


class BranchReportService:
    @staticmethod
    def run(*, report: str, scope: ReportScope, date_from=None, date_to=None) -> dict:
        from apps.settings_app.models import Branch

        if report not in REPORTS:
            raise ReportScopeError({"report": f"Unknown report. Choose one of {', '.join(REPORTS)}."})
        ids = list(scope.branch_ids)
        unassigned_ok = report == "profit-loss" and scope.covers_all and scope.mode == "consolidated"
        if report == "sales":
            grouped, total = _sales(ids, date_from, date_to)
        elif report == "stock-value":
            grouped, total = _stock_value(ids, date_from, date_to)
        elif report == "cash":
            grouped, total = _cash(ids, date_from, date_to)
        elif report == "purchases":
            grouped, total = _purchases(ids, date_from, date_to)
        elif report == "inventory":
            grouped, total = _inventory(ids, date_from, date_to)
        elif report == "expenses":
            grouped, total = _expenses(ids, date_from, date_to)
        elif report == "transfers":
            grouped, total = _transfers(ids, date_from, date_to)
        else:
            grouped, total = _pnl(ids, date_from, date_to, include_unassigned=unassigned_ok)

        empty = {k: ZERO for k in total}
        rows = []
        summed = dict(empty)
        for branch in Branch.active_objects().filter(pk__in=ids).order_by("name"):
            figures = {**empty, **grouped.get(branch.pk, {})}
            for k, v in figures.items():
                summed[k] = summed.get(k, ZERO) + v
            rows.append(
                {
                    "branch_id": str(branch.pk),
                    "branch_code": branch.code,
                    "branch_name": branch.name,
                    **_fl(_derive(report, figures)),
                }
            )
        result = {
            "report": report,
            "mode": scope.mode,
            "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None,
            "branches": rows,
        }
        if unassigned_ok:
            un = {**empty, **grouped.get(None, {})}
            for k, v in un.items():
                summed[k] = summed.get(k, ZERO) + v
            result["unassigned"] = _fl(_derive(report, un))
        result["consolidated"] = _fl(_derive(report, total))
        result["reconciles"] = all(
            abs(summed.get(k, ZERO) - total.get(k, ZERO)) < Decimal("0.0001") for k in total
        )
        return result


def branch_overview(*, scope: ReportScope, date_from=None, date_to=None) -> dict:
    """One row per branch in ``scope`` for the Branch Management list: status, manager, structure
    counts and headline figures. Figures come from :class:`BranchReportService` (never recomputed
    here), so the list, the dashboard and the reports always agree."""
    from datetime import date

    from django.db.models import Count, Q
    from django.utils import timezone

    from apps.inventory.models import Warehouse
    from apps.organization.models import CashRegister, PosTerminal, UserBranchAccess
    from apps.sales.models import CashierSession
    from apps.settings_app.models import Branch

    ids = list(scope.branch_ids)
    today = timezone.localdate()
    reports = {
        name: {r["branch_id"]: r for r in BranchReportService.run(report=name, scope=scope, date_from=date_from, date_to=date_to)["branches"]}
        for name in ("sales", "stock-value", "inventory", "transfers")
    }

    def counts(qs, field):
        return dict(qs.filter(**{f"{field}__in": ids}).order_by().values_list(field).annotate(n=Count("id")))

    effective = Q(status=UserBranchAccess.STATUS_ACTIVE) & (Q(starts_on__isnull=True) | Q(starts_on__lte=today)) & (
        Q(ends_on__isnull=True) | Q(ends_on__gte=today))
    access = UserBranchAccess.active_objects().filter(effective, branch_id__in=ids)
    users = dict(access.order_by().values_list("branch_id").annotate(n=Count("user_id", distinct=True)))
    managers = {}
    for row in access.filter(access_profile__is_manager=True).select_related("user"):
        managers.setdefault(row.branch_id, []).append(row.user.get_full_name() or row.user.username)
    warehouses = counts(Warehouse.active_objects(), "branch_id")
    terminals = counts(PosTerminal.active_objects().filter(status="ACTIVE"), "branch_id")
    registers = counts(CashRegister.active_objects().filter(status="ACTIVE"), "branch_id")
    shifts = counts(CashierSession.active_objects().filter(status=CashierSession.STATUS_OPEN), "branch_id")

    rows = []
    for b in Branch.active_objects().filter(pk__in=ids).select_related("manager", "company").order_by("-is_default", "name"):
        key = str(b.pk)
        sales, stock, inv, tr = (reports[n].get(key, {}) for n in ("sales", "stock-value", "inventory", "transfers"))
        manager_names = managers.get(b.pk, [])
        if b.manager_id:
            manager_names = [b.manager.get_full_name() or b.manager.username] + [m for m in manager_names if m != (b.manager.get_full_name() or b.manager.username)]
        rows.append({
            "branch_id": key, "code": b.code, "name": b.name, "status": b.status, "is_active": b.is_active,
            "is_default": b.is_default, "branch_type": getattr(b, "branch_type", ""), "phone": b.phone,
            "address": b.address,
            "company_id": str(b.company_id) if b.company_id else None,
            "company_name": b.company.name if b.company_id else "",
            "managers": manager_names,
            "users": users.get(b.pk, 0), "warehouses": warehouses.get(b.pk, 0),
            "pos_terminals": terminals.get(b.pk, 0), "cash_registers": registers.get(b.pk, 0),
            "open_shifts": shifts.get(b.pk, 0),
            "sales_net": sales.get("net", 0.0), "sales_invoices": sales.get("invoices", 0.0),
            "stock_value": stock.get("value", 0.0), "low_stock": inv.get("low_stock", 0.0),
            "out_of_stock": inv.get("out_of_stock", 0.0),
            "transfers_open": tr.get("outgoing_open", 0.0) + tr.get("incoming_open", 0.0),
            "transfers_awaiting_approval": tr.get("awaiting_approval", 0.0),
        })
    return {"mode": scope.mode, "date_from": str(date_from) if date_from else None,
            "date_to": str(date_to) if date_to else None, "branches": rows}
