"""B4-11: transfer state transitions notify only the relevant branch audience."""

from __future__ import annotations

from decimal import Decimal

import pytest

from apps.notifications.models import Notification
from apps.inventory.services.branch_transfer_service import BranchTransferService, TransferLineInput
from tests.helpers.branch_factory import add_owner, add_product, build_branch_tenant, grant, set_inventory

pytestmark = pytest.mark.django_db


@pytest.fixture
def ctx():
    return build_branch_tenant(slug="btr-notif-tenant")


def test_request_notifies_source_branch_transfer_holders_only(ctx):
    owner = add_owner(ctx, username="notif_owner")
    other_branch_only = add_owner(ctx, username="notif_other")  # also has all branches via add_owner
    product = add_product(ctx, sku="NOTIF-1")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))

    req = BranchTransferService.request_transfer(
        source_branch_id=ctx.branch("HODAN").pk,
        destination_branch_id=ctx.branch("BAKAARO").pk,
        source_warehouse_id=ctx.warehouse("HODAN").pk,
        destination_warehouse_id=ctx.warehouse("BAKAARO").pk,
        lines=[TransferLineInput(product_id=product.pk, quantity=Decimal("2"))],
        user=owner,
    )

    notif = Notification.objects.filter(notification_type="branch_transfer", metadata__event="requested").first()
    assert notif is not None
    assert notif.metadata["request_id"] == str(req.pk)
    # The requester is never notified about their own action.
    assert not Notification.objects.filter(user=owner, metadata__event="requested").exists()


def test_no_notification_for_users_without_branch_access(ctx):
    from tests.helpers.branch_factory import add_user

    owner = add_owner(ctx, username="notif_owner2")
    outsider = add_user(ctx, username="notif_outsider", role_slug="admin")  # no branch grants at all
    product = add_product(ctx, sku="NOTIF-2")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))

    BranchTransferService.request_transfer(
        source_branch_id=ctx.branch("HODAN").pk,
        destination_branch_id=ctx.branch("BAKAARO").pk,
        source_warehouse_id=ctx.warehouse("HODAN").pk,
        destination_warehouse_id=ctx.warehouse("BAKAARO").pk,
        lines=[TransferLineInput(product_id=product.pk, quantity=Decimal("2"))],
        user=owner,
    )
    assert not Notification.objects.filter(user=outsider).exists()


def test_receive_notifies_source_branch(ctx):
    owner = add_owner(ctx, username="notif_owner3")
    add_owner(ctx, username="notif_owner3_source_staff")  # someone other than the actor to notify
    product = add_product(ctx, sku="NOTIF-3")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    req = BranchTransferService.request_transfer(
        source_branch_id=ctx.branch("HODAN").pk,
        destination_branch_id=ctx.branch("BAKAARO").pk,
        source_warehouse_id=ctx.warehouse("HODAN").pk,
        destination_warehouse_id=ctx.warehouse("BAKAARO").pk,
        lines=[TransferLineInput(product_id=product.pk, quantity=Decimal("2"))],
        user=owner,
    )
    req = BranchTransferService.approve(request_id=req.pk, user=owner)
    req = BranchTransferService.reserve(request_id=req.pk, user=owner)
    req = BranchTransferService.dispatch(request_id=req.pk, user=owner)
    BranchTransferService.receive(request_id=req.pk, user=owner)

    assert Notification.objects.filter(notification_type="branch_transfer", metadata__event="received").exists()


# --------------------------------------------------------------------------- #
# Phase 6 — B6-5 / B6-6: branch, severity, entity and audience; no duplicate storms
# --------------------------------------------------------------------------- #


def _branch_users(ctx):
    from tests.helpers.branch_factory import add_user, make_profile

    staff = make_profile(tenant=ctx.tenant, code="STAFF", name="Staff", codenames=["inventory.view"])
    boss = make_profile(
        tenant=ctx.tenant, code="BOSS", name="Boss", codenames=["inventory.view"], is_manager=True
    )
    hodan_staff = add_user(ctx, username="n6_hodan_staff", role_slug="admin")
    hodan_boss = add_user(ctx, username="n6_hodan_boss", role_slug="admin")
    bakaaro_staff = add_user(ctx, username="n6_bakaaro_staff", role_slug="admin")
    grant(ctx, user=hodan_staff, branch_code="HODAN", profile=staff)
    grant(ctx, user=hodan_boss, branch_code="HODAN", profile=boss)
    grant(ctx, user=bakaaro_staff, branch_code="BAKAARO", profile=staff)
    return hodan_staff, hodan_boss, bakaaro_staff


def test_branch_alert_carries_branch_severity_entity_and_audience(ctx):
    from apps.notifications.services.notification_service import NotificationService

    hodan_staff, hodan_boss, bakaaro_staff = _branch_users(ctx)
    created = NotificationService.notify_branch(
        branch=ctx.branch("HODAN"),
        permission="inventory.view",
        notification_type="low_stock",
        title="Low", message="m", severity="CRITICAL",
        entity_type="inventory", entity_id="abc",
        action_url="/inventory", dedupe_key="b65:1",
    )
    assert created == 2  # both Hodan users; nobody from Bakaaro, nobody without access
    n = Notification.objects.get(user=hodan_staff)
    assert (n.branch_id, n.severity, n.entity_type, n.entity_id, n.audience, n.action_url) == (
        ctx.branch("HODAN").pk, "CRITICAL", "inventory", "abc", "BRANCH", "/inventory",
    )
    assert not Notification.objects.filter(user=bakaaro_staff).exists()


def test_managers_only_audience_excludes_ordinary_branch_staff(ctx):
    from apps.notifications.services.notification_service import NotificationService

    hodan_staff, hodan_boss, _ = _branch_users(ctx)
    NotificationService.notify_branch(
        branch=ctx.branch("HODAN"), managers_only=True, notification_type="system",
        title="t", message="m", dedupe_key="b65:mgr",
    )
    assert Notification.objects.filter(user=hodan_boss, audience="BRANCH_MANAGERS").count() == 1
    assert not Notification.objects.filter(user=hodan_staff).exists()


def test_list_filters_by_branch_and_severity_and_hides_expired(ctx):
    from datetime import timedelta

    from django.utils import timezone

    from apps.notifications.services.notification_service import NotificationService

    hodan_staff, _, _ = _branch_users(ctx)
    grant(ctx, user=hodan_staff, branch_code="BAKAARO")
    common = dict(tenant=ctx.tenant, user=hodan_staff, notification_type="system", message="m")
    Notification.objects.create(title="h-warn", branch=ctx.branch("HODAN"), severity="WARNING", **common)
    Notification.objects.create(title="b-info", branch=ctx.branch("BAKAARO"), **common)
    Notification.objects.create(title="tenant-wide", **common)
    Notification.objects.create(
        title="old", branch=ctx.branch("HODAN"), expires_at=timezone.now() - timedelta(hours=1), **common
    )

    titles = lambda **kw: {n.title for n in NotificationService.list(user=hodan_staff, **kw)}  # noqa: E731
    assert titles() == {"h-warn", "b-info", "tenant-wide"}  # expired hidden
    assert titles(branch_ids=[ctx.branch("HODAN").pk]) == {"h-warn", "tenant-wide"}
    assert titles(severity="WARNING") == {"h-warn"}


def test_transfer_alert_is_tagged_with_branch_entity_and_severity(ctx):
    owner = add_owner(ctx, username="n6_transfer_owner")
    add_owner(ctx, username="n6_transfer_peer")  # the actor is never alerted; the peer is
    product = add_product(ctx, sku="N6-T")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    req = BranchTransferService.request_transfer(
        source_branch_id=ctx.branch("HODAN").pk, destination_branch_id=ctx.branch("BAKAARO").pk,
        source_warehouse_id=ctx.warehouse("HODAN").pk, destination_warehouse_id=ctx.warehouse("BAKAARO").pk,
        lines=[TransferLineInput(product_id=product.pk, quantity=Decimal("2"))], user=owner,
    )
    n = Notification.objects.filter(metadata__event="requested").first()
    assert (n.branch_id, n.entity_type, n.entity_id, n.severity) == (
        ctx.branch("HODAN").pk, "branch_transfer", str(req.pk), "INFO",
    )


def test_low_stock_scan_alerts_each_branch_audience_once(ctx):
    from apps.notifications.tasks.scheduled import scan_low_stock

    _branch_users(ctx)
    product = add_product(ctx, sku="N6-LOW", minimum_stock=5)
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("1"))
    set_inventory(ctx, product=product, branch_code="BAKAARO", quantity=Decimal("50"))

    first = scan_low_stock()["notifications_created"]
    second = scan_low_stock()["notifications_created"]
    third = scan_low_stock()["notifications_created"]

    low = Notification.objects.filter(notification_type="low_stock")
    assert first == 2 and (second, third) == (0, 0)  # Hodan's two users, once each
    assert {n.branch_id for n in low} == {ctx.branch("HODAN").pk}  # not Bakaaro, which is fine
    assert {n.severity for n in low} == {"WARNING"}


def test_out_of_stock_is_critical(ctx):
    from apps.notifications.tasks.scheduled import scan_low_stock

    _branch_users(ctx)
    product = add_product(ctx, sku="N6-OUT", minimum_stock=5)
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("0"))
    scan_low_stock()
    assert set(Notification.objects.filter(notification_type="low_stock").values_list("severity", flat=True)) == {"CRITICAL"}


def test_transfer_event_alert_fires_once_even_if_replayed(ctx):
    from apps.inventory.services.branch_transfer_service import _notify_transfer_event

    owner = add_owner(ctx, username="n6_replay_owner")
    add_owner(ctx, username="n6_replay_peer")
    product = add_product(ctx, sku="N6-R")
    set_inventory(ctx, product=product, branch_code="HODAN", quantity=Decimal("10"))
    req = BranchTransferService.request_transfer(
        source_branch_id=ctx.branch("HODAN").pk, destination_branch_id=ctx.branch("BAKAARO").pk,
        source_warehouse_id=ctx.warehouse("HODAN").pk, destination_warehouse_id=ctx.warehouse("BAKAARO").pk,
        lines=[TransferLineInput(product_id=product.pk, quantity=Decimal("2"))], user=owner,
    )
    before = Notification.objects.filter(metadata__event="requested").count()
    assert before == 1
    for _ in range(3):
        _notify_transfer_event(req, event="requested", actor=owner)
    assert Notification.objects.filter(metadata__event="requested").count() == before


def test_cash_variance_alerts_branch_managers_once_per_shift(ctx):
    from apps.sales.services.cashier_session_service import CashierSessionService
    from tests.helpers.branch_factory import add_user
    from tests.unit.test_branch_pos import make_terminal

    hodan_staff, hodan_boss, _ = _branch_users(ctx)
    cashier = add_user(ctx, username="n6_cashier", role_slug="cashier", branches=("HODAN",))
    make_terminal(ctx)
    session = CashierSessionService.open_session(user=cashier, branch_id=ctx.branch("HODAN").pk)
    CashierSessionService.close_session(session_id=session.pk, user=cashier, closing_cash_counted=-80)
    session.refresh_from_db()
    CashierSessionService._alert_variance(session, actor=cashier)  # replay: no second alert

    alerts = Notification.objects.filter(notification_type="cash_variance")
    assert [a.user_id for a in alerts] == [hodan_boss.pk]  # managers of that branch only
    a = alerts.get()
    assert (a.severity, a.entity_type, a.entity_id, a.branch_id) == (
        "CRITICAL", "cashier_session", str(session.pk), ctx.branch("HODAN").pk,
    )
