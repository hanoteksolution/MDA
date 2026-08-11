"""WBS (Work Breakdown Structure) services."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_date

from apps.audit.services import write_audit
from apps.project_management.models import WbsNode
from apps.project_management.services.project_service import ProjectService
from core.tenancy import apply_tenant_scope, stamp_tenant_id


def _as_date(value):
    if value is None or value == "":
        return None
    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value
    return parse_date(str(value)[:10])


class WbsError(ValueError):
    pass


class WbsService:
    @staticmethod
    def _scope_nodes(qs, *, user=None, request=None, branch_id=None):
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(project__branch_id=branch_id)
        qs = qs.filter(project__is_archived=False)
        return qs

    @staticmethod
    def list_nodes(*, project_id=None, search=None, user=None, request=None, branch_id=None):
        qs = WbsNode.active_objects().select_related("project", "parent")
        if project_id:
            qs = qs.filter(project_id=project_id)
        qs = WbsService._scope_nodes(qs, user=user, request=request, branch_id=branch_id)
        if search:
            term = search.strip()
            qs = qs.filter(
                Q(code__icontains=term)
                | Q(name__icontains=term)
                | Q(description__icontains=term)
            )
        return qs.order_by("level", "sort_order", "code")

    @staticmethod
    def get_node(*, pk, user=None, request=None):
        qs = WbsNode.active_objects().select_related("project", "parent")
        qs = WbsService._scope_nodes(qs, user=user, request=request)
        return qs.get(pk=pk)

    @staticmethod
    def _next_code(*, project_id, prefix="WBS") -> str:
        count = WbsNode.objects.filter(project_id=project_id).count() + 1
        return f"{prefix}-{count:04d}"

    @staticmethod
    def _validate_parent(*, project_id, parent_id, node_id=None):
        if not parent_id:
            return None
        if node_id and str(parent_id) == str(node_id):
            raise WbsError("A node cannot be its own parent.")
        parent = WbsNode.active_objects().filter(pk=parent_id, project_id=project_id).first()
        if not parent:
            raise WbsError("Parent WBS node not found for this project.")
        if node_id:
            cursor = parent
            while cursor:
                if str(cursor.id) == str(node_id):
                    raise WbsError("Cannot move node under its own descendant.")
                cursor = cursor.parent if cursor.parent_id else None
        return parent

    @staticmethod
    def build_tree(nodes) -> list[dict]:
        from apps.project_management.serializers.wbs_serializers import serialize_wbs_node

        by_parent: dict[str | None, list] = {}
        for node in nodes:
            key = str(node.parent_id) if node.parent_id else None
            by_parent.setdefault(key, []).append(node)

        def walk(parent_id=None):
            items = by_parent.get(parent_id, [])
            return [
                {**serialize_wbs_node(n), "children": walk(str(n.id))}
                for n in items
            ]

        return walk(None)

    @staticmethod
    @transaction.atomic
    def create_node(*, data, user=None, request=None) -> WbsNode:
        payload = stamp_tenant_id(dict(data or {}), user=user, request=request)
        project_id = payload.get("project_id")
        if not project_id:
            raise WbsError("project_id is required.")
        project = ProjectService.get_project(pk=project_id, user=user, request=request)
        name = (payload.get("name") or "").strip()
        if not name:
            raise WbsError("WBS node name is required.")
        code = (payload.get("code") or "").strip()
        if not code:
            code = WbsService._next_code(project_id=project.id)

        parent = WbsService._validate_parent(
            project_id=project.id, parent_id=payload.get("parent_id")
        )
        row = WbsNode(
            tenant_id=project.tenant_id,
            project=project,
            parent=parent,
            code=code,
            name=name,
            node_type=payload.get("node_type") or WbsNode.TYPE_WORK_PACKAGE,
            description=(payload.get("description") or "").strip(),
            sort_order=int(payload.get("sort_order") or 0),
            planned_start=_as_date(payload.get("planned_start")),
            planned_end=_as_date(payload.get("planned_end")),
            status=payload.get("status") or WbsNode.STATUS_NOT_STARTED,
            progress_percent=Decimal(str(payload.get("progress_percent") or 0)),
            estimated_hours=Decimal(str(payload.get("estimated_hours") or 0)),
            estimated_cost=Decimal(str(payload.get("estimated_cost") or 0)),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
        row.recalc_level()
        row.save()
        write_audit(
            action="create",
            module="project_management",
            entity=row,
            user=user,
            request=request,
            new_values={"code": row.code, "project_id": str(project.id)},
        )
        return row

    @staticmethod
    @transaction.atomic
    def update_node(*, node: WbsNode, data, user=None, request=None) -> WbsNode:
        payload = dict(data or {})
        if "name" in payload:
            name = (payload.get("name") or "").strip()
            if not name:
                raise WbsError("WBS node name is required.")
            node.name = name
        if "code" in payload:
            code = (payload.get("code") or "").strip()
            if not code:
                raise WbsError("WBS code is required.")
            node.code = code
        if "node_type" in payload and payload.get("node_type"):
            node.node_type = payload["node_type"]
        if "description" in payload:
            node.description = (payload.get("description") or "").strip()
        if "sort_order" in payload:
            node.sort_order = int(payload.get("sort_order") or 0)
        if "parent_id" in payload:
            node.parent = WbsService._validate_parent(
                project_id=node.project_id,
                parent_id=payload.get("parent_id"),
                node_id=node.id,
            )
            node.recalc_level()
        for field in ("planned_start", "planned_end", "actual_start", "actual_end"):
            if field in payload:
                setattr(node, field, _as_date(payload.get(field)))
        if "status" in payload and payload.get("status"):
            node.status = payload["status"]
        if "progress_percent" in payload:
            node.progress_percent = Decimal(str(payload.get("progress_percent") or 0))
        if "estimated_hours" in payload:
            node.estimated_hours = Decimal(str(payload.get("estimated_hours") or 0))
        if "estimated_cost" in payload:
            node.estimated_cost = Decimal(str(payload.get("estimated_cost") or 0))
        if "notes" in payload:
            node.notes = (payload.get("notes") or "").strip()
        node.updated_by = user
        node.save()
        write_audit(
            action="update",
            module="project_management",
            entity=node,
            user=user,
            request=request,
        )
        return node

    @staticmethod
    @transaction.atomic
    def move_node(*, node: WbsNode, parent_id, user=None, request=None) -> WbsNode:
        node.parent = WbsService._validate_parent(
            project_id=node.project_id,
            parent_id=parent_id,
            node_id=node.id,
        )
        node.recalc_level()
        node.updated_by = user
        node.save()
        write_audit(
            action="move",
            module="project_management",
            entity=node,
            user=user,
            request=request,
            new_values={"parent_id": str(parent_id) if parent_id else None},
        )
        return node

    @staticmethod
    def soft_delete_node(*, node: WbsNode, user=None, request=None) -> WbsNode:
        if WbsNode.active_objects().filter(parent_id=node.id).exists():
            raise WbsError("Remove or reassign child nodes before deleting this node.")
        node.soft_delete(user=user)
        write_audit(
            action="delete",
            module="project_management",
            entity=node,
            user=user,
            request=request,
        )
        return node
