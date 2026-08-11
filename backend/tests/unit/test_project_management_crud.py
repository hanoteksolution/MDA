"""Project Management CRUD API tests."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models.audit_log import AuditLog
from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import Role
from apps.platform.models import Tenant
from apps.platform.services.module_service import sync_tenant_modules
from apps.platform.services.platform_service import PlatformService
from apps.project_management.models import Project
from apps.products.models import Category, Product, Unit
from apps.purchases.models import PurchaseOrder
from apps.settings_app.models import Branch, Company
from apps.suppliers.models import Supplier


@pytest.fixture
def pm_env(db):
    bootstrap_roles_and_permissions()
    PlatformService.ensure_default_business_types()
    tenant = Tenant.objects.create(name="PM Co", slug="pm-co", status=Tenant.STATUS_ACTIVE)
    company = Company.objects.create(name="PM Co", tenant=tenant)
    branch = Branch.objects.create(
        company=company, tenant=tenant, name="HQ", code="HQ", is_default=True
    )
    sync_tenant_modules(
        tenant=tenant,
        enabled_codes=["project_management", "finance"],
        validate_dependencies=False,
    )
    user = get_user_model().objects.create_user(
        username="pm_admin",
        password="pass12345",
        tenant=tenant,
        branch=branch,
        role=Role.objects.get(slug="super_admin"),
    )
    from apps.finance.services.chart_service import ChartService
    from apps.finance.services.mapping_service import MappingService
    from apps.finance.services.period_service import PeriodService

    ChartService.ensure_default_chart(tenant_id=tenant.id, user=user)
    MappingService.seed_defaults(tenant_id=tenant.id, user=user)
    PeriodService.ensure_current(user=user)
    return {"tenant": tenant, "branch": branch, "user": user}


def _client(user):
    client = APIClient()
    token = str(RefreshToken.for_user(user).access_token)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client


@pytest.mark.django_db
def test_project_crud_lifecycle(pm_env):
    client = _client(pm_env["user"])
    branch_id = str(pm_env["branch"].id)

    created = client.post(
        "/api/v1/projects/",
        {
            "name": "Tower Block A",
            "branch_id": branch_id,
            "project_type": "construction",
            "budget": "500000",
            "expected_revenue": "650000",
            "cost_estimate": "420000",
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    body = created.json()["data"]
    project_id = body["id"]
    assert body["status"] == "draft"
    assert body["project_code"].startswith("PRJ-")
    assert body["profit_estimate"] == 230000.0

    listed = client.get(f"/api/v1/projects/?branch_id={branch_id}")
    assert listed.status_code == 200
    assert listed.json()["data"]["count"] >= 1

    patched = client.patch(
        f"/api/v1/projects/{project_id}/",
        {"name": "Tower Block A — Phase 1", "progress_percent": "5"},
        format="json",
    )
    assert patched.status_code == 200
    assert patched.json()["data"]["name"] == "Tower Block A — Phase 1"

    for status in ("planning", "approved", "active"):
        res = client.post(
            f"/api/v1/projects/{project_id}/status/",
            {"status": status},
            format="json",
        )
        assert res.status_code == 200, res.content
        assert res.json()["data"]["status"] == status

    dup = client.post(f"/api/v1/projects/{project_id}/duplicate/", {}, format="json")
    assert dup.status_code == 201
    assert dup.json()["data"]["status"] == "draft"

    archived = client.delete(f"/api/v1/projects/{project_id}/")
    assert archived.status_code == 200
    assert Project.active_objects().filter(pk=project_id).exists() is False

    restored = client.post(f"/api/v1/projects/{project_id}/restore/", {}, format="json")
    assert restored.status_code == 200
    assert Project.active_objects().filter(pk=project_id).exists() is True
    assert restored.json()["data"]["is_archived"] is False

    summary = client.get(f"/api/v1/projects/summary/?branch_id={branch_id}")
    assert summary.status_code == 200
    assert summary.json()["data"]["total_projects"] >= 2

    assert AuditLog.objects.filter(module="project_management", action="create").exists()


@pytest.mark.django_db
def test_project_budget_crud(pm_env):
    client = _client(pm_env["user"])
    branch_id = str(pm_env["branch"].id)
    project = client.post(
        "/api/v1/projects/",
        {"name": "Budget Test", "branch_id": branch_id},
        format="json",
    ).json()["data"]

    created = client.post(
        "/api/v1/projects/budgets/",
        {
            "project_id": project["id"],
            "name": "Baseline Budget",
            "lines": [
                {"category": "labor", "description": "Site crew", "planned_amount": "10000"},
                {"category": "materials", "description": "Concrete", "planned_amount": "25000"},
            ],
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    budget = created.json()["data"]
    assert budget["total_planned"] == 35000.0
    budget_id = budget["id"]

    approved = client.post(
        f"/api/v1/projects/budgets/{budget_id}/status/",
        {"status": "submitted"},
        format="json",
    )
    assert approved.status_code == 200
    approved = client.post(
        f"/api/v1/projects/budgets/{budget_id}/status/",
        {"status": "approved"},
        format="json",
    )
    assert approved.status_code == 200
    assert approved.json()["data"]["status"] == "approved"


@pytest.mark.django_db
def test_project_wbs_tree_crud(pm_env):
    client = _client(pm_env["user"])
    branch_id = str(pm_env["branch"].id)
    project = client.post(
        "/api/v1/projects/",
        {"name": "WBS Test", "branch_id": branch_id},
        format="json",
    ).json()["data"]

    phase = client.post(
        "/api/v1/projects/wbs/",
        {
            "project_id": project["id"],
            "name": "Phase 1",
            "node_type": "phase",
        },
        format="json",
    )
    assert phase.status_code == 201, phase.content
    phase_id = phase.json()["data"]["id"]

    package = client.post(
        "/api/v1/projects/wbs/",
        {
            "project_id": project["id"],
            "parent_id": phase_id,
            "name": "Foundation",
            "node_type": "work_package",
        },
        format="json",
    )
    assert package.status_code == 201
    assert package.json()["data"]["level"] == 1

    tree = client.get(f"/api/v1/projects/wbs/?tree=1&project_id={project['id']}")
    assert tree.status_code == 200
    nodes = tree.json()["data"]
    assert len(nodes) == 1
    assert len(nodes[0]["children"]) == 1

    updated = client.patch(
        f"/api/v1/projects/wbs/{phase_id}/",
        {"progress_percent": "25", "status": "in_progress"},
        format="json",
    )
    assert updated.status_code == 200
    assert float(updated.json()["data"]["progress_percent"]) == 25.0

    package_id = package.json()["data"]["id"]
    assert client.delete(f"/api/v1/projects/wbs/{phase_id}/").status_code == 400
    assert client.delete(f"/api/v1/projects/wbs/{package_id}/").status_code == 200
    assert client.delete(f"/api/v1/projects/wbs/{phase_id}/").status_code == 200


@pytest.mark.django_db
def test_project_task_crud_and_status(pm_env):
    client = _client(pm_env["user"])
    branch_id = str(pm_env["branch"].id)
    project = client.post(
        "/api/v1/projects/",
        {"name": "Task Test", "branch_id": branch_id},
        format="json",
    ).json()["data"]

    created = client.post(
        "/api/v1/projects/tasks/",
        {
            "project_id": project["id"],
            "title": "Pour foundation",
            "priority": "high",
            "estimated_hours": "24",
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    task = created.json()["data"]
    assert task["task_code"].startswith("TASK-")
    task_id = task["id"]

    updated = client.patch(
        f"/api/v1/projects/tasks/{task_id}/",
        {"progress_percent": "50", "actual_hours": "12"},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["progress_percent"] == 50.0

    for status in ("in_progress", "review", "done"):
        response = client.post(
            f"/api/v1/projects/tasks/{task_id}/status/",
            {"status": status},
            format="json",
        )
        assert response.status_code == 200, response.content
        assert response.json()["data"]["status"] == status

    assert client.delete(f"/api/v1/projects/tasks/{task_id}/").status_code == 200
    assert client.get(f"/api/v1/projects/tasks/{task_id}/").status_code == 404


@pytest.mark.django_db
def test_project_milestone_crud_and_status(pm_env):
    client = _client(pm_env["user"])
    branch_id = str(pm_env["branch"].id)
    project = client.post(
        "/api/v1/projects/",
        {"name": "Milestone Test", "branch_id": branch_id},
        format="json",
    ).json()["data"]

    created = client.post(
        "/api/v1/projects/milestones/",
        {
            "project_id": project["id"],
            "name": "Foundation complete",
            "due_date": "2026-09-01",
            "is_critical": True,
        },
        format="json",
    )
    assert created.status_code == 201, created.content
    milestone = created.json()["data"]
    assert milestone["code"].startswith("MS-")
    milestone_id = milestone["id"]

    updated = client.patch(
        f"/api/v1/projects/milestones/{milestone_id}/",
        {"name": "Foundation inspection complete"},
        format="json",
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["name"] == "Foundation inspection complete"

    achieved = client.post(
        f"/api/v1/projects/milestones/{milestone_id}/status/",
        {"status": "achieved"},
        format="json",
    )
    assert achieved.status_code == 200
    assert achieved.json()["data"]["completed_at"] is not None

    assert client.delete(f"/api/v1/projects/milestones/{milestone_id}/").status_code == 200
    assert client.get(f"/api/v1/projects/milestones/{milestone_id}/").status_code == 404


@pytest.mark.django_db
def test_project_invalid_status_transition(pm_env):
    client = _client(pm_env["user"])
    branch_id = str(pm_env["branch"].id)
    created = client.post(
        "/api/v1/projects/",
        {"name": "Quick Job", "branch_id": branch_id},
        format="json",
    )
    project_id = created.json()["data"]["id"]
    bad = client.post(
        f"/api/v1/projects/{project_id}/status/",
        {"status": "active"},
        format="json",
    )
    assert bad.status_code == 400


@pytest.mark.django_db
def test_construction_hierarchy_create(pm_env):
    client = _client(pm_env["user"])
    project = client.post("/api/v1/projects/", {"name": "Hierarchy", "branch_id": str(pm_env["branch"].id)}, format="json").json()["data"]
    site = client.post("/api/v1/projects/sites/", {"project_id": project["id"], "code": "S1", "name": "Main"}, format="json")
    assert site.status_code == 201, site.content
    building = client.post("/api/v1/projects/buildings/", {"project_id": project["id"], "site_id": site.json()["data"]["id"], "code": "B1", "name": "Tower"}, format="json")
    assert building.status_code == 201, building.content
    floor = client.post("/api/v1/projects/floors/", {"project_id": project["id"], "building_id": building.json()["data"]["id"], "code": "F1", "name": "Level 1"}, format="json")
    assert floor.status_code == 201, floor.content
    unit = client.post("/api/v1/projects/units/", {"project_id": project["id"], "building_id": building.json()["data"]["id"], "floor_id": floor.json()["data"]["id"], "code": "U1", "name": "101"}, format="json")
    assert unit.status_code == 201, unit.content


@pytest.mark.django_db
def test_boq_lines_and_approval(pm_env):
    client = _client(pm_env["user"])
    project = client.post("/api/v1/projects/", {"name": "BOQ", "branch_id": str(pm_env["branch"].id)}, format="json").json()["data"]
    created = client.post("/api/v1/projects/boq/", {"project_id": project["id"], "name": "Baseline", "lines": [{"item_code": "LAB-1", "description": "Crew", "quantity": "10", "unit_rate": "25"}]}, format="json")
    assert created.status_code == 201, created.content
    boq = created.json()["data"]
    assert boq["total_amount"] == 250.0
    assert client.post(f"/api/v1/projects/boq/{boq['id']}/status/", {"status": "submitted"}, format="json").status_code == 200
    approved = client.post(f"/api/v1/projects/boq/{boq['id']}/status/", {"status": "approved"}, format="json")
    assert approved.status_code == 200
    assert approved.json()["data"]["approved_at"] is not None


@pytest.mark.django_db
def test_worker_rate_snapshots_preserve_attendance_and_wage(pm_env):
    client = _client(pm_env["user"])
    project = client.post("/api/v1/projects/", {"name": "Wages", "branch_id": str(pm_env["branch"].id)}, format="json").json()["data"]
    worker = client.post("/api/v1/projects/workers/", {"project_id": project["id"], "code": "W1", "full_name": "Mason", "daily_rate": "100"}, format="json")
    assert worker.status_code == 201, worker.content
    worker_id = worker.json()["data"]["id"]
    attendance = client.post("/api/v1/projects/attendance/", {"project_id": project["id"], "worker_id": worker_id, "work_date": "2026-08-11", "hours_worked": "8"}, format="json")
    assert attendance.status_code == 201, attendance.content
    wage = client.post("/api/v1/projects/wages/", {"attendance_id": attendance.json()["data"]["id"]}, format="json")
    assert wage.status_code == 201, wage.content
    assert client.patch(f"/api/v1/projects/workers/{worker_id}/", {"daily_rate": "150"}, format="json").status_code == 200
    assert client.get(f"/api/v1/projects/attendance/{attendance.json()['data']['id']}/").json()["data"]["rate_applied"] == 100.0
    assert client.get(f"/api/v1/projects/wages/{wage.json()['data']['id']}/").json()["data"]["amount"] == 800.0


@pytest.mark.django_db
def test_change_order_approval(pm_env):
    client = _client(pm_env["user"])
    project = client.post("/api/v1/projects/", {"name": "Operations", "branch_id": str(pm_env["branch"].id)}, format="json").json()["data"]
    change = client.post("/api/v1/projects/change-orders/", {"project_id": project["id"], "code": "CO-1", "title": "Extra steel", "amount_delta": "1200"}, format="json")
    assert change.status_code == 201, change.content
    approved = client.post(f"/api/v1/projects/change-orders/{change.json()['data']['id']}/status/", {"status": "approved"}, format="json")
    assert approved.status_code == 200
    assert approved.json()["data"]["approved_at"] is not None


@pytest.mark.django_db
def test_safety_incident_create(pm_env):
    client = _client(pm_env["user"])
    project = client.post("/api/v1/projects/", {"name": "Safety", "branch_id": str(pm_env["branch"].id)}, format="json").json()["data"]
    incident = client.post("/api/v1/projects/safety-incidents/", {"project_id": project["id"], "incident_date": "2026-08-11", "severity": "high", "title": "Near miss", "description": "Scaffold access"}, format="json")
    assert incident.status_code == 201, incident.content
    assert incident.json()["data"]["status"] == "open"


@pytest.mark.django_db
def test_invoice_accounting_preview(pm_env):
    client = _client(pm_env["user"])
    project = client.post("/api/v1/projects/", {"name": "Billing", "branch_id": str(pm_env["branch"].id)}, format="json").json()["data"]
    invoice = client.post("/api/v1/projects/invoices/", {"project_id": project["id"], "invoice_number": "INV-1", "invoice_date": "2026-08-11", "amount": "1000", "tax_amount": "100", "total_amount": "1100"}, format="json")
    assert invoice.status_code == 201, invoice.content
    preview = client.post(f"/api/v1/projects/invoices/{invoice.json()['data']['id']}/accounting-preview/", {}, format="json")
    assert preview.status_code == 200, preview.content
    data = preview.json()["data"]
    assert data["already_posted"] is False
    assert data["lines"][0]["debit"] == 1100.0
    assert data["lines"][0]["account_code"]  # real CoA code, not placeholder
    assert data["lines"][0]["account_code"] != "AR-PLACEHOLDER"


@pytest.mark.django_db
def test_invoice_posts_to_central_ledger(pm_env):
    from apps.finance.models import JournalEntry

    client = _client(pm_env["user"])
    project = client.post(
        "/api/v1/projects/",
        {"name": "Ledger Job", "branch_id": str(pm_env["branch"].id)},
        format="json",
    ).json()["data"]
    invoice = client.post(
        "/api/v1/projects/invoices/",
        {
            "project_id": project["id"],
            "invoice_number": "INV-GL-1",
            "invoice_date": "2026-08-11",
            "amount": "1000",
            "tax_amount": "100",
            "total_amount": "1100",
        },
        format="json",
    )
    assert invoice.status_code == 201, invoice.content
    invoice_id = invoice.json()["data"]["id"]

    posted = client.post(f"/api/v1/projects/invoices/{invoice_id}/post-accounting/", {}, format="json")
    assert posted.status_code == 200, posted.content
    body = posted.json()["data"]
    assert body["status"] == "issued"
    assert body["journal_entry_id"]
    assert body["posted_at"]

    entry = JournalEntry.objects.get(pk=body["journal_entry_id"])
    assert entry.status == JournalEntry.STATUS_POSTED
    assert entry.source_module == "project_management"
    lines = list(entry.lines.filter(deleted_at__isnull=True))
    assert abs(sum(float(l.debit) for l in lines) - sum(float(l.credit) for l in lines)) < 0.01
    assert sum(float(l.debit) for l in lines) == 1100.0

    # Idempotent second post
    again = client.post(f"/api/v1/projects/invoices/{invoice_id}/post-accounting/", {}, format="json")
    assert again.status_code == 200
    assert again.json()["data"]["journal_entry_id"] == body["journal_entry_id"]


@pytest.mark.django_db
def test_project_inventory_allocation_crud(pm_env):
    client = _client(pm_env["user"])
    project = client.post(
        "/api/v1/projects/", {"name": "Inventory Job", "branch_id": str(pm_env["branch"].id)}, format="json"
    ).json()["data"]
    category = Category.objects.create(name="Materials", tenant=pm_env["tenant"])
    unit = Unit.objects.create(name="Each", abbreviation="ea", tenant=pm_env["tenant"])
    product = Product.objects.create(
        tenant=pm_env["tenant"], sku="CEMENT-01", name="Cement", category=category, unit=unit,
        cost_price="10", selling_price="12",
    )
    created = client.post(
        "/api/v1/projects/inventory-allocations/",
        {"project_id": project["id"], "product_id": str(product.id), "quantity": "5", "unit_cost": "10", "source_type": "manual"},
        format="json",
    )
    assert created.status_code == 201, created.content
    allocation = created.json()["data"]
    assert allocation["quantity"] == 5.0
    assert allocation["product_id"] == str(product.id)
    assert client.get(f"/api/v1/projects/inventory-allocations/?project_id={project['id']}").status_code == 200


@pytest.mark.django_db
def test_purchase_order_accepts_project_dimension(pm_env):
    project = Project.objects.create(
        tenant=pm_env["tenant"], branch=pm_env["branch"], project_code="PRJ-PO", name="PO Project"
    )
    supplier = Supplier.objects.create(tenant=pm_env["tenant"], supplier_code="SUP-PO", company_name="Materials Co")
    order = PurchaseOrder.objects.create(
        tenant=pm_env["tenant"], branch=pm_env["branch"], supplier=supplier,
        order_number="PO-PROJECT-1", project=project,
    )
    assert order.project_id == project.id
