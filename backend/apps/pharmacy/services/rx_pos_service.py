"""POS prescription gate — require active Rx for Rx-only products (PHASE 16)."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from apps.pharmacy.models import Prescription
from apps.pharmacy.services.prescription_service import PrescriptionService
from apps.platform.services.module_service import tenant_has_module
from apps.products.models import Product
from core.tenancy import apply_tenant_scope


class RxPosError(ValueError):
    pass


class RxPosService:
    @staticmethod
    def pharmacy_gate_applies(*, profile=None, user=None) -> bool:
        profile = profile or {}
        code = (profile.get("code") or "").strip().upper()
        mods = {str(m).lower() for m in (profile.get("enabled_modules") or [])}
        caps = profile.get("capabilities") or {}
        if code == "PHARMACY":
            return True
        if "pharmacy" in mods and (caps.get("batches") or caps.get("rx") or caps.get("prescriptions")):
            return True
        if user is not None and tenant_has_module("pharmacy", user=user):
            return True
        return False

    @staticmethod
    def _remaining_by_product(lines) -> dict[str, Decimal]:
        avail: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for line in lines:
            remaining = line.quantity_remaining
            if remaining <= 0:
                continue
            if line.product_id:
                avail[str(line.product_id)] += remaining
        return avail

    @staticmethod
    def _free_text_remaining(lines, product_name: str) -> Decimal:
        pname = (product_name or "").strip().lower()
        if not pname:
            return Decimal("0")
        total = Decimal("0")
        for line in lines:
            if line.product_id:
                continue
            remaining = line.quantity_remaining
            if remaining <= 0:
                continue
            drug = (line.drug_name or "").strip().lower()
            if drug and (pname in drug or drug in pname):
                total += remaining
        return total

    @staticmethod
    def validate_cart(
        *,
        items,
        prescription_id=None,
        user=None,
        request=None,
        profile=None,
    ):
        """Return Prescription when gate applies and Rx is valid; else None.

        Raises RxPosError when Rx-required products are in the cart without a
        covering active prescription, or cart qty exceeds Rx remaining.
        """
        if not items:
            return None
        if not RxPosService.pharmacy_gate_applies(profile=profile, user=user):
            return None

        product_ids = [item["product_id"] for item in items if item.get("product_id")]
        if not product_ids:
            return None

        products = list(
            apply_tenant_scope(
                Product.active_objects().filter(pk__in=product_ids),
                user=user,
                request=request,
            )
        )
        by_id = {str(p.id): p for p in products}
        rx_needed = [
            by_id[str(pid)]
            for pid in product_ids
            if str(pid) in by_id and by_id[str(pid)].requires_prescription
        ]
        seen = set()
        unique_needed = []
        for p in rx_needed:
            if p.id in seen:
                continue
            seen.add(p.id)
            unique_needed.append(p)

        if not unique_needed:
            return None

        if not prescription_id:
            names = ", ".join(p.name for p in unique_needed[:3])
            more = f" (+{len(unique_needed) - 3} more)" if len(unique_needed) > 3 else ""
            raise RxPosError(
                f"Prescription required for: {names}{more}. Select an active Rx at checkout."
            )

        rx = (
            PrescriptionService.list(user=user, request=request)
            .filter(pk=prescription_id)
            .prefetch_related("lines")
            .first()
        )
        if rx is None:
            raise RxPosError("Prescription not found.")
        if rx.status == Prescription.STATUS_CANCELLED:
            raise RxPosError("Cannot use a cancelled prescription.")
        if rx.status == Prescription.STATUS_DISPENSED:
            raise RxPosError("Prescription already dispensed.")
        if rx.status not in (Prescription.STATUS_ACTIVE, Prescription.STATUS_DRAFT):
            raise RxPosError(f"Prescription status '{rx.status}' cannot be used at POS.")

        lines = list(rx.lines.filter(deleted_at__isnull=True))
        covered_product_ids = {str(line.product_id) for line in lines if line.product_id}
        free_text = [
            (line.drug_name or "").strip().lower()
            for line in lines
            if not line.product_id and (line.drug_name or "").strip()
        ]
        avail = RxPosService._remaining_by_product(lines)

        cart_qty: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for item in items:
            pid = str(item.get("product_id") or "")
            if pid:
                cart_qty[pid] += Decimal(str(item.get("quantity") or 0))

        for product in unique_needed:
            pid = str(product.id)
            if pid not in covered_product_ids:
                pname = (product.name or "").strip().lower()
                if not (pname and any(pname in drug or drug in pname for drug in free_text if drug)):
                    raise RxPosError(
                        f"Prescription {rx.rx_number} does not cover '{product.name}'. "
                        "Add the product on the Rx or pick another prescription."
                    )
                available = RxPosService._free_text_remaining(lines, product.name)
            else:
                available = avail.get(pid, Decimal("0"))

            need = cart_qty.get(pid, Decimal("0"))
            if need > available:
                raise RxPosError(
                    f"Cart quantity {need} exceeds Rx remaining {available} "
                    f"for '{product.name}' on {rx.rx_number}."
                )

        return rx
