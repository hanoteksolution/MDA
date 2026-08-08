"""Attribute engine — resolve, validate, and persist product EAV values."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction
from django.db.models import Q
from django.utils.dateparse import parse_date, parse_datetime

from apps.products.models import (
    AttributeDefinition,
    AttributeOption,
    BusinessTypeAttribute,
    CategoryAttribute,
    Product,
    ProductAttributeValue,
)
from core.tenancy import resolve_acting_tenant, stamp_tenant_id


class AttributeValidationError(ValueError):
    pass


class AttributeService:
    @staticmethod
    def list_definitions(*, user=None, request=None, include_system=True, is_active=True):
        qs = AttributeDefinition.active_objects().prefetch_related("options")
        tenant = resolve_acting_tenant(user=user, request=request)
        if tenant is None:
            qs = qs.filter(tenant__isnull=True)
        elif include_system:
            qs = qs.filter(Q(tenant_id=tenant.id) | Q(tenant__isnull=True))
        else:
            qs = qs.filter(tenant_id=tenant.id)
        if is_active is not None:
            qs = qs.filter(is_active=is_active)
        return qs.order_by("sort_order", "name")

    @staticmethod
    def create_definition(*, data, user=None, request=None):
        payload = {
            "code": (data.get("code") or "").strip().lower().replace(" ", "_"),
            "name": (data.get("name") or "").strip(),
            "description": data.get("description") or "",
            "data_type": data.get("data_type") or AttributeDefinition.TYPE_TEXT,
            "is_required": bool(data.get("is_required", False)),
            "is_searchable": bool(data.get("is_searchable", False)),
            "is_filterable": bool(data.get("is_filterable", False)),
            "is_pos_visible": bool(data.get("is_pos_visible", False)),
            "is_reportable": bool(data.get("is_reportable", False)),
            "is_active": bool(data.get("is_active", True)),
            "sort_order": int(data.get("sort_order") or 100),
        }
        if not payload["code"]:
            raise AttributeValidationError("Attribute code is required.")
        if not payload["name"]:
            raise AttributeValidationError("Attribute name is required.")
        valid_types = {c[0] for c in AttributeDefinition.TYPE_CHOICES}
        if payload["data_type"] not in valid_types:
            raise AttributeValidationError(f"Invalid data_type: {payload['data_type']}")
        payload = stamp_tenant_id(payload, user=user, request=request)
        definition = AttributeDefinition.objects.create(**payload, created_by=user)
        for idx, opt in enumerate(data.get("options") or []):
            AttributeService._create_option(definition, opt, sort_order=idx * 10, user=user)
        return definition

    @staticmethod
    def update_definition(*, definition, data, user=None):
        writable = (
            "name",
            "description",
            "is_required",
            "is_searchable",
            "is_filterable",
            "is_pos_visible",
            "is_reportable",
            "is_active",
            "sort_order",
        )
        for key in writable:
            if key in data:
                setattr(definition, key, data[key])
        if definition.tenant_id is not None:
            if "data_type" in data:
                definition.data_type = data["data_type"]
            if data.get("code"):
                definition.code = str(data["code"]).strip().lower().replace(" ", "_")
        definition.updated_by = user
        definition.save()
        if "options" in data and definition.data_type in (
            AttributeDefinition.TYPE_SELECT,
            AttributeDefinition.TYPE_MULTI_SELECT,
        ):
            AttributeService._replace_options(definition, data["options"] or [], user=user)
        return definition

    @staticmethod
    def _create_option(definition, opt, *, sort_order=100, user=None):
        if isinstance(opt, str):
            value = label = opt.strip()
            is_active = True
        else:
            value = str(opt.get("value") or opt.get("label") or "").strip()
            label = str(opt.get("label") or value).strip()
            sort_order = int(opt.get("sort_order") or sort_order)
            is_active = bool(opt.get("is_active", True))
        if not value:
            raise AttributeValidationError("Option value is required.")
        return AttributeOption.objects.create(
            definition=definition,
            value=value,
            label=label,
            sort_order=sort_order,
            is_active=is_active,
            created_by=user,
        )

    @staticmethod
    def _replace_options(definition, options, *, user=None):
        existing = {
            o.value: o
            for o in AttributeOption.active_objects().filter(definition=definition)
        }
        seen = set()
        for idx, opt in enumerate(options):
            if isinstance(opt, str):
                value = label = opt.strip()
                sort_order = idx * 10
                is_active = True
            else:
                value = str(opt.get("value") or opt.get("label") or "").strip()
                label = str(opt.get("label") or value).strip()
                sort_order = int(opt.get("sort_order") or idx * 10)
                is_active = bool(opt.get("is_active", True))
            if not value:
                continue
            seen.add(value)
            row = existing.get(value)
            if row:
                row.label = label
                row.sort_order = sort_order
                row.is_active = is_active
                row.updated_by = user
                row.save()
            else:
                AttributeService._create_option(
                    definition,
                    {
                        "value": value,
                        "label": label,
                        "sort_order": sort_order,
                        "is_active": is_active,
                    },
                    user=user,
                )
        for value, row in existing.items():
            if value not in seen:
                row.soft_delete(user=user)

    @staticmethod
    def assign_to_business_type(
        *, business_type_id, definition_id, is_required=None, sort_order=100, user=None
    ):
        obj = BusinessTypeAttribute.objects.filter(
            business_type_id=business_type_id, definition_id=definition_id
        ).first()
        if obj is None:
            return BusinessTypeAttribute.objects.create(
                business_type_id=business_type_id,
                definition_id=definition_id,
                is_required=is_required,
                sort_order=sort_order,
                created_by=user,
            )
        obj.is_required = is_required
        obj.sort_order = sort_order
        obj.deleted_at = None
        obj.deleted_by = None
        obj.updated_by = user
        obj.save()
        return obj

    @staticmethod
    def assign_to_category(
        *, category_id, definition_id, is_required=None, sort_order=100, user=None
    ):
        obj = CategoryAttribute.objects.filter(
            category_id=category_id, definition_id=definition_id
        ).first()
        if obj is None:
            return CategoryAttribute.objects.create(
                category_id=category_id,
                definition_id=definition_id,
                is_required=is_required,
                sort_order=sort_order,
                created_by=user,
            )
        obj.is_required = is_required
        obj.sort_order = sort_order
        obj.deleted_at = None
        obj.deleted_by = None
        obj.updated_by = user
        obj.save()
        return obj

    @staticmethod
    def resolve_applicable(
        *,
        user=None,
        request=None,
        category_id=None,
        business_type_id=None,
        product=None,
    ):
        """Return ordered list of {definition, is_required, source} for a product context."""
        tenant = resolve_acting_tenant(user=user, request=request)
        if product is not None:
            category_id = category_id or product.category_id
            if tenant is None:
                tenant = product.tenant

        if business_type_id is None and tenant is not None:
            business_type_id = getattr(tenant, "business_type_id", None)

        def_ids = set()
        required_map: dict = {}
        source_map: dict = {}
        sort_map: dict = {}

        if business_type_id:
            for link in (
                BusinessTypeAttribute.active_objects()
                .filter(business_type_id=business_type_id)
                .select_related("definition")
            ):
                defn = link.definition
                if defn.deleted_at or not defn.is_active:
                    continue
                if tenant and defn.tenant_id and defn.tenant_id != tenant.id:
                    continue
                def_ids.add(defn.id)
                required_map[defn.id] = (
                    link.is_required if link.is_required is not None else defn.is_required
                )
                source_map[defn.id] = "business_type"
                sort_map[defn.id] = link.sort_order

        if category_id:
            for link in (
                CategoryAttribute.active_objects()
                .filter(category_id=category_id)
                .select_related("definition")
            ):
                defn = link.definition
                if defn.deleted_at or not defn.is_active:
                    continue
                if tenant and defn.tenant_id and defn.tenant_id != tenant.id:
                    continue
                def_ids.add(defn.id)
                if link.is_required is not None:
                    required_map[defn.id] = link.is_required
                elif defn.id not in required_map:
                    required_map[defn.id] = defn.is_required
                source_map[defn.id] = (
                    "both" if source_map.get(defn.id) == "business_type" else "category"
                )
                sort_map[defn.id] = min(sort_map.get(defn.id, 9999), link.sort_order)

        if not def_ids:
            return []

        defs = (
            AttributeDefinition.active_objects()
            .filter(id__in=def_ids, is_active=True)
            .prefetch_related("options")
        )
        by_id = {d.id: d for d in defs}
        ordered = sorted(
            def_ids,
            key=lambda i: (
                sort_map.get(i, by_id[i].sort_order if i in by_id else 999),
                by_id[i].name if i in by_id else "",
            ),
        )
        result = []
        for did in ordered:
            defn = by_id.get(did)
            if not defn:
                continue
            result.append(
                {
                    "definition": defn,
                    "is_required": bool(required_map.get(did, defn.is_required)),
                    "source": source_map.get(did, "unknown"),
                }
            )
        return result

    @staticmethod
    def serialize_definition(defn: AttributeDefinition, *, is_required=None, source=None) -> dict:
        options = [
            {
                "id": str(o.id),
                "value": o.value,
                "label": o.label,
                "sort_order": o.sort_order,
                "is_active": o.is_active,
            }
            for o in defn.options.all()
            if o.deleted_at is None and o.is_active
        ]
        data = {
            "id": str(defn.id),
            "code": defn.code,
            "name": defn.name,
            "description": defn.description,
            "data_type": defn.data_type,
            "is_required": defn.is_required if is_required is None else is_required,
            "is_searchable": defn.is_searchable,
            "is_filterable": defn.is_filterable,
            "is_pos_visible": defn.is_pos_visible,
            "is_reportable": defn.is_reportable,
            "is_active": defn.is_active,
            "sort_order": defn.sort_order,
            "tenant_id": str(defn.tenant_id) if defn.tenant_id else None,
            "is_system": defn.tenant_id is None,
            "options": options,
        }
        if source is not None:
            data["source"] = source
        return data

    @staticmethod
    def serialize_value(row: ProductAttributeValue) -> dict:
        defn = row.definition
        raw = AttributeService._extract_python_value(row, defn.data_type)
        return {
            "definition_id": str(defn.id),
            "code": defn.code,
            "name": defn.name,
            "data_type": defn.data_type,
            "value": AttributeService._jsonable(raw),
            "option_id": str(row.option_id) if row.option_id else None,
            "is_pos_visible": defn.is_pos_visible,
        }

    @staticmethod
    def values_for_product(product: Product) -> list[dict]:
        rows = (
            ProductAttributeValue.active_objects()
            .filter(product=product)
            .select_related("definition", "option")
        )
        return [AttributeService.serialize_value(r) for r in rows]

    @staticmethod
    def _extract_python_value(row: ProductAttributeValue, data_type: str):
        if data_type == AttributeDefinition.TYPE_TEXT:
            return row.value_text or ""
        if data_type == AttributeDefinition.TYPE_INT:
            return row.value_int
        if data_type == AttributeDefinition.TYPE_DECIMAL:
            return row.value_decimal
        if data_type == AttributeDefinition.TYPE_BOOL:
            return row.value_bool
        if data_type == AttributeDefinition.TYPE_DATE:
            return row.value_date
        if data_type == AttributeDefinition.TYPE_DATETIME:
            return row.value_datetime
        if data_type == AttributeDefinition.TYPE_SELECT:
            return row.option.value if row.option_id else (row.value_text or None)
        if data_type == AttributeDefinition.TYPE_MULTI_SELECT:
            return list(row.value_json or [])
        return row.value_text

    @staticmethod
    def _jsonable(value):
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    @staticmethod
    def _is_empty(value) -> bool:
        if value is None:
            return True
        if isinstance(value, str) and not value.strip():
            return True
        if isinstance(value, (list, dict)) and len(value) == 0:
            return True
        return False

    @staticmethod
    def _coerce(definition: AttributeDefinition, raw: Any) -> dict:
        empty = {
            "value_text": "",
            "value_int": None,
            "value_decimal": None,
            "value_bool": None,
            "value_date": None,
            "value_datetime": None,
            "value_json": [],
            "option": None,
        }
        if AttributeService._is_empty(raw):
            return empty

        dt = definition.data_type
        if dt == AttributeDefinition.TYPE_TEXT:
            empty["value_text"] = str(raw)
            return empty
        if dt == AttributeDefinition.TYPE_INT:
            try:
                empty["value_int"] = int(raw)
            except (TypeError, ValueError) as exc:
                raise AttributeValidationError(f"{definition.name} must be an integer.") from exc
            return empty
        if dt == AttributeDefinition.TYPE_DECIMAL:
            try:
                empty["value_decimal"] = Decimal(str(raw))
            except (InvalidOperation, TypeError, ValueError) as exc:
                raise AttributeValidationError(f"{definition.name} must be a number.") from exc
            return empty
        if dt == AttributeDefinition.TYPE_BOOL:
            if isinstance(raw, bool):
                empty["value_bool"] = raw
            elif str(raw).lower() in ("1", "true", "yes", "y"):
                empty["value_bool"] = True
            elif str(raw).lower() in ("0", "false", "no", "n"):
                empty["value_bool"] = False
            else:
                raise AttributeValidationError(f"{definition.name} must be true/false.")
            return empty
        if dt == AttributeDefinition.TYPE_DATE:
            if isinstance(raw, date) and not isinstance(raw, datetime):
                empty["value_date"] = raw
            else:
                parsed = parse_date(str(raw)[:10])
                if not parsed:
                    raise AttributeValidationError(
                        f"{definition.name} must be a date (YYYY-MM-DD)."
                    )
                empty["value_date"] = parsed
            return empty
        if dt == AttributeDefinition.TYPE_DATETIME:
            if isinstance(raw, datetime):
                empty["value_datetime"] = raw
            else:
                parsed = parse_datetime(str(raw))
                if not parsed:
                    raise AttributeValidationError(f"{definition.name} must be a datetime.")
                empty["value_datetime"] = parsed
            return empty
        if dt == AttributeDefinition.TYPE_SELECT:
            options = list(
                AttributeOption.active_objects().filter(definition=definition, is_active=True)
            )
            by_value = {o.value: o for o in options}
            by_id = {str(o.id): o for o in options}
            key = str(raw)
            opt = by_value.get(key) or by_id.get(key)
            if not opt:
                raise AttributeValidationError(f"Invalid option for {definition.name}.")
            empty["option"] = opt
            empty["value_text"] = opt.value
            return empty
        if dt == AttributeDefinition.TYPE_MULTI_SELECT:
            if not isinstance(raw, (list, tuple)):
                raw = [raw]
            options = list(
                AttributeOption.active_objects().filter(definition=definition, is_active=True)
            )
            by_value = {o.value: o for o in options}
            by_id = {str(o.id): o for o in options}
            values = []
            for item in raw:
                key = str(item)
                opt = by_value.get(key) or by_id.get(key)
                if not opt:
                    raise AttributeValidationError(
                        f"Invalid option '{item}' for {definition.name}."
                    )
                values.append(opt.value)
            empty["value_json"] = values
            return empty
        raise AttributeValidationError(f"Unsupported data_type: {dt}")

    @staticmethod
    def _normalize_incoming(attributes: list | dict | None) -> dict[str, Any]:
        incoming: dict[str, Any] = {}
        if attributes is None:
            return incoming
        if isinstance(attributes, dict):
            for k, v in attributes.items():
                incoming[str(k)] = v
            return incoming
        for item in attributes:
            if not isinstance(item, dict):
                continue
            key = item.get("definition_id") or item.get("code")
            if key:
                incoming[str(key)] = item.get("value")
        return incoming

    @staticmethod
    def _lookup_definition(key: str, *, tenant) -> AttributeDefinition | None:
        q = Q(id=key) | Q(code=key)
        if tenant is not None:
            q &= Q(tenant_id=tenant.id) | Q(tenant__isnull=True)
        return AttributeDefinition.active_objects().filter(q, is_active=True).first()

    @staticmethod
    @transaction.atomic
    def set_product_attributes(
        *,
        product: Product,
        attributes: list | dict | None,
        user=None,
        request=None,
        validate_required: bool = True,
    ):
        """Persist attribute payload (list of {definition_id|code, value} or dict)."""
        applicable = AttributeService.resolve_applicable(
            user=user, request=request, product=product
        )
        by_id = {str(a["definition"].id): a for a in applicable}
        by_code = {a["definition"].code: a for a in applicable}
        incoming = AttributeService._normalize_incoming(attributes)
        tenant = resolve_acting_tenant(user=user, request=request) or product.tenant

        for key, raw in incoming.items():
            meta = by_id.get(key) or by_code.get(key)
            defn = meta["definition"] if meta else AttributeService._lookup_definition(
                key, tenant=tenant
            )
            if not defn:
                raise AttributeValidationError(f"Unknown attribute: {key}")
            if meta and meta["is_required"] and AttributeService._is_empty(raw):
                raise AttributeValidationError(f"{defn.name} is required.")

            coerced = AttributeService._coerce(defn, raw)
            row = ProductAttributeValue.objects.filter(
                product=product, definition=defn
            ).first()

            if AttributeService._is_empty(raw):
                if row and row.deleted_at is None:
                    row.soft_delete(user=user)
                continue

            if row is None:
                ProductAttributeValue.objects.create(
                    product=product, definition=defn, created_by=user, **coerced
                )
            else:
                row.deleted_at = None
                row.deleted_by = None
                for field, value in coerced.items():
                    setattr(row, field, value)
                row.updated_by = user
                row.save()

        if validate_required:
            for item in applicable:
                if not item["is_required"]:
                    continue
                defn = item["definition"]
                row = (
                    ProductAttributeValue.active_objects()
                    .filter(product=product, definition=defn)
                    .first()
                )
                if row is None or AttributeService._is_empty(
                    AttributeService._extract_python_value(row, defn.data_type)
                ):
                    # Only enforce when attributes were supplied (create/update with attrs)
                    # or definition is required — always enforce if validate_required.
                    raise AttributeValidationError(f"{defn.name} is required.")

        return AttributeService.values_for_product(product)
