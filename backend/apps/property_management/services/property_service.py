"""Property management services (PHASE 18 skeleton)."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.property_management.models import (
    Building,
    MaintenanceRequest,
    Owner,
    PropertyAsset,
    PropertyDocument,
    PropertyUnit,
)
from apps.settings_app.models import Branch
from core.tenancy import apply_tenant_scope, stamp_tenant_id


class PropertyError(ValueError):
    pass


class PropertyService:
    @staticmethod
    def _scope(qs, *, user=None, request=None, branch_id=None):
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        return qs

    @staticmethod
    def _require_branch(*, branch_id, user=None, request=None) -> Branch:
        if not branch_id:
            raise PropertyError("branch_id is required.")
        qs = apply_tenant_scope(Branch.active_objects(), user=user, request=request)
        branch = qs.filter(pk=branch_id).first()
        if not branch:
            branch = Branch.active_objects().filter(pk=branch_id).first()
        if not branch:
            raise PropertyError("Branch not found for this tenant.")
        return branch

    # --- Summary ---
    @staticmethod
    def summary(*, branch_id=None, user=None, request=None) -> dict:
        units = PropertyService.list_units(
            branch_id=branch_id, user=user, request=request
        )
        maint = PropertyService.list_maintenance(
            branch_id=branch_id, user=user, request=request
        )
        return {
            "properties": PropertyService.list_properties(
                branch_id=branch_id, user=user, request=request
            )
            .filter(is_active=True)
            .count(),
            "buildings": PropertyService.list_buildings(
                branch_id=branch_id, user=user, request=request
            )
            .filter(is_active=True)
            .count(),
            "units": units.filter(is_active=True).count(),
            "units_vacant": units.filter(
                is_active=True, status=PropertyUnit.STATUS_VACANT
            ).count(),
            "units_occupied": units.filter(
                is_active=True, status=PropertyUnit.STATUS_OCCUPIED
            ).count(),
            "units_maintenance": units.filter(
                is_active=True, status=PropertyUnit.STATUS_MAINTENANCE
            ).count(),
            "owners": PropertyService.list_owners(
                branch_id=branch_id, user=user, request=request
            ).count(),
            "maintenance_open": maint.filter(
                status__in=[
                    MaintenanceRequest.STATUS_OPEN,
                    MaintenanceRequest.STATUS_IN_PROGRESS,
                ]
            ).count(),
            "documents": PropertyService.list_documents(
                branch_id=branch_id, user=user, request=request
            ).count(),
        }

    # --- Owners ---
    @staticmethod
    def list_owners(*, branch_id=None, user=None, request=None):
        qs = Owner.active_objects().select_related("branch")
        qs = apply_tenant_scope(qs, user=user, request=request)
        if branch_id:
            qs = qs.filter(Q(branch_id=branch_id) | Q(branch_id__isnull=True))
        return qs.order_by("full_name")

    @staticmethod
    def get_owner(*, pk, user=None, request=None):
        return PropertyService.list_owners(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_owner(*, data, user=None, request=None) -> Owner:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = None
        if payload.get("branch_id"):
            branch = PropertyService._require_branch(
                branch_id=payload.get("branch_id"), user=user, request=request
            )
        name = (payload.get("full_name") or "").strip()
        if not name:
            raise PropertyError("Owner full_name is required.")
        return Owner.objects.create(
            tenant_id=payload.get("tenant_id")
            or (branch.tenant_id if branch else None),
            branch=branch,
            full_name=name,
            phone=(payload.get("phone") or "").strip(),
            email=(payload.get("email") or "").strip(),
            notes=(payload.get("notes") or "").strip(),
            is_active=bool(payload.get("is_active", True)),
            created_by=user,
        )

    # --- Properties ---
    @staticmethod
    def list_properties(*, branch_id=None, user=None, request=None):
        qs = PropertyAsset.active_objects().select_related("branch", "owner")
        return PropertyService._scope(
            qs, user=user, request=request, branch_id=branch_id
        ).order_by("name")

    @staticmethod
    def get_property(*, pk, user=None, request=None):
        return PropertyService.list_properties(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_property(*, data, user=None, request=None) -> PropertyAsset:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = PropertyService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        name = (payload.get("name") or "").strip()
        if not name:
            raise PropertyError("Property name is required.")
        owner = None
        if payload.get("owner_id"):
            owner = PropertyService.get_owner(
                pk=payload["owner_id"], user=user, request=request
            )
        kind = payload.get("kind") or PropertyAsset.KIND_MIXED
        if kind not in dict(PropertyAsset.KIND_CHOICES):
            raise PropertyError(f"Invalid property kind: {kind}")
        return PropertyAsset.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            owner=owner,
            name=name,
            code=(payload.get("code") or "").strip(),
            kind=kind,
            address=(payload.get("address") or "").strip(),
            city=(payload.get("city") or "").strip(),
            notes=(payload.get("notes") or "").strip(),
            is_active=bool(payload.get("is_active", True)),
            created_by=user,
        )

    # --- Buildings ---
    @staticmethod
    def list_buildings(*, branch_id=None, property_id=None, user=None, request=None):
        qs = Building.active_objects().select_related("branch", "property_asset")
        qs = PropertyService._scope(qs, user=user, request=request, branch_id=branch_id)
        if property_id:
            qs = qs.filter(property_asset_id=property_id)
        return qs.order_by("name")

    @staticmethod
    def get_building(*, pk, user=None, request=None):
        return PropertyService.list_buildings(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_building(*, data, user=None, request=None) -> Building:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        prop = PropertyService.get_property(
            pk=payload.get("property_id") or payload.get("property_asset_id"),
            user=user,
            request=request,
        )
        branch = PropertyService._require_branch(
            branch_id=payload.get("branch_id") or prop.branch_id,
            user=user,
            request=request,
        )
        name = (payload.get("name") or "").strip()
        if not name:
            raise PropertyError("Building name is required.")
        return Building.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            property_asset=prop,
            name=name,
            code=(payload.get("code") or "").strip(),
            floors=int(payload.get("floors") or 1),
            notes=(payload.get("notes") or "").strip(),
            is_active=bool(payload.get("is_active", True)),
            created_by=user,
        )

    # --- Units ---
    @staticmethod
    def list_units(
        *, branch_id=None, building_id=None, status=None, user=None, request=None
    ):
        qs = PropertyUnit.active_objects().select_related(
            "branch", "building", "building__property_asset"
        )
        qs = PropertyService._scope(qs, user=user, request=request, branch_id=branch_id)
        if building_id:
            qs = qs.filter(building_id=building_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("code")

    @staticmethod
    def get_unit(*, pk, user=None, request=None):
        return PropertyService.list_units(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_unit(*, data, user=None, request=None) -> PropertyUnit:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        building = PropertyService.get_building(
            pk=payload.get("building_id"), user=user, request=request
        )
        branch = PropertyService._require_branch(
            branch_id=payload.get("branch_id") or building.branch_id,
            user=user,
            request=request,
        )
        code = (payload.get("code") or "").strip()
        if not code:
            raise PropertyError("Unit code is required.")
        kind = payload.get("kind") or PropertyUnit.KIND_RESIDENTIAL
        if kind not in dict(PropertyUnit.KIND_CHOICES):
            raise PropertyError(f"Invalid unit kind: {kind}")
        status = payload.get("status") or PropertyUnit.STATUS_VACANT
        if status not in dict(PropertyUnit.STATUS_CHOICES):
            raise PropertyError(f"Invalid unit status: {status}")
        area = payload.get("area_sqm")
        return PropertyUnit.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            building=building,
            code=code,
            label=(payload.get("label") or code).strip(),
            floor=(payload.get("floor") or "").strip(),
            kind=kind,
            status=status,
            bedrooms=int(payload.get("bedrooms") or 0),
            bathrooms=int(payload.get("bathrooms") or 0),
            area_sqm=Decimal(str(area)) if area not in (None, "") else None,
            rent_amount=Decimal(str(payload.get("rent_amount") or 0)),
            deposit_amount=Decimal(str(payload.get("deposit_amount") or 0)),
            notes=(payload.get("notes") or "").strip(),
            is_active=bool(payload.get("is_active", True)),
            created_by=user,
        )

    @staticmethod
    def set_unit_status(*, unit: PropertyUnit, status: str, user=None) -> PropertyUnit:
        if status not in dict(PropertyUnit.STATUS_CHOICES):
            raise PropertyError(f"Invalid unit status: {status}")
        unit.status = status
        unit.updated_by = user
        unit.save(update_fields=["status", "updated_by", "updated_at"])
        return unit

    # --- Maintenance ---
    @staticmethod
    def list_maintenance(*, branch_id=None, status=None, user=None, request=None):
        qs = MaintenanceRequest.active_objects().select_related(
            "branch", "unit", "unit__building"
        )
        qs = PropertyService._scope(qs, user=user, request=request, branch_id=branch_id)
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-created_at")

    @staticmethod
    def get_maintenance(*, pk, user=None, request=None):
        return PropertyService.list_maintenance(user=user, request=request).get(pk=pk)

    @staticmethod
    @transaction.atomic
    def create_maintenance(*, data, user=None, request=None) -> MaintenanceRequest:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        unit = PropertyService.get_unit(
            pk=payload.get("unit_id"), user=user, request=request
        )
        branch = PropertyService._require_branch(
            branch_id=payload.get("branch_id") or unit.branch_id,
            user=user,
            request=request,
        )
        title = (payload.get("title") or "").strip()
        if not title:
            raise PropertyError("Maintenance title is required.")
        priority = payload.get("priority") or MaintenanceRequest.PRIORITY_NORMAL
        if priority not in dict(MaintenanceRequest.PRIORITY_CHOICES):
            raise PropertyError(f"Invalid priority: {priority}")
        row = MaintenanceRequest.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            unit=unit,
            title=title,
            description=(payload.get("description") or "").strip(),
            status=MaintenanceRequest.STATUS_OPEN,
            priority=priority,
            reported_by=(payload.get("reported_by") or "").strip(),
            created_by=user,
        )
        if payload.get("set_unit_maintenance", True):
            PropertyService.set_unit_status(
                unit=unit, status=PropertyUnit.STATUS_MAINTENANCE, user=user
            )
        return row

    @staticmethod
    @transaction.atomic
    def update_maintenance_status(
        *, request_row: MaintenanceRequest, status: str, user=None
    ) -> MaintenanceRequest:
        if status not in dict(MaintenanceRequest.STATUS_CHOICES):
            raise PropertyError(f"Invalid maintenance status: {status}")
        request_row.status = status
        request_row.updated_by = user
        if status == MaintenanceRequest.STATUS_DONE:
            request_row.completed_at = timezone.now()
            PropertyService.set_unit_status(
                unit=request_row.unit, status=PropertyUnit.STATUS_VACANT, user=user
            )
        elif status == MaintenanceRequest.STATUS_CANCELLED:
            # Only free unit if no other open maintenance
            open_left = (
                MaintenanceRequest.active_objects()
                .filter(
                    unit_id=request_row.unit_id,
                    status__in=[
                        MaintenanceRequest.STATUS_OPEN,
                        MaintenanceRequest.STATUS_IN_PROGRESS,
                    ],
                )
                .exclude(pk=request_row.pk)
                .exists()
            )
            if not open_left and request_row.unit.status == PropertyUnit.STATUS_MAINTENANCE:
                PropertyService.set_unit_status(
                    unit=request_row.unit, status=PropertyUnit.STATUS_VACANT, user=user
                )
        request_row.save()
        return request_row

    # --- Documents ---
    @staticmethod
    def list_documents(*, branch_id=None, property_id=None, unit_id=None, user=None, request=None):
        qs = PropertyDocument.active_objects().select_related(
            "branch", "property_asset", "unit"
        )
        qs = PropertyService._scope(qs, user=user, request=request, branch_id=branch_id)
        if property_id:
            qs = qs.filter(property_asset_id=property_id)
        if unit_id:
            qs = qs.filter(unit_id=unit_id)
        return qs.order_by("-created_at")

    @staticmethod
    @transaction.atomic
    def create_document(*, data, user=None, request=None) -> PropertyDocument:
        payload = stamp_tenant_id(dict(data), user=user, request=request)
        branch = PropertyService._require_branch(
            branch_id=payload.get("branch_id"), user=user, request=request
        )
        title = (payload.get("title") or "").strip()
        if not title:
            raise PropertyError("Document title is required.")
        prop = None
        unit = None
        if payload.get("property_id") or payload.get("property_asset_id"):
            prop = PropertyService.get_property(
                pk=payload.get("property_id") or payload.get("property_asset_id"),
                user=user,
                request=request,
            )
        if payload.get("unit_id"):
            unit = PropertyService.get_unit(
                pk=payload["unit_id"], user=user, request=request
            )
        if not prop and not unit:
            raise PropertyError("Attach document to a property or unit.")
        return PropertyDocument.objects.create(
            tenant_id=payload.get("tenant_id") or branch.tenant_id,
            branch=branch,
            property_asset=prop,
            unit=unit,
            title=title,
            doc_type=(payload.get("doc_type") or "other").strip(),
            file_url=(payload.get("file_url") or "").strip(),
            notes=(payload.get("notes") or "").strip(),
            created_by=user,
        )
