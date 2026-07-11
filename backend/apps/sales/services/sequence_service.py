"""Atomic per-branch document serial numbers for accountable counting."""

from django.db import IntegrityError, transaction

from apps.sales.models import DocumentSequence, Invoice, Quotation
from apps.settings_app.models import Branch


class DocumentSequenceService:
    PREFIX = {
        DocumentSequence.KIND_ORDER_SLIP: "OSL",
        DocumentSequence.KIND_HOLD_SLIP: "HLD",
        DocumentSequence.KIND_INVOICE: "INV",
        DocumentSequence.KIND_QUOTATION: "QT",
    }

    @staticmethod
    def _seed_value(*, branch: Branch, kind: str) -> int:
        if kind == DocumentSequence.KIND_INVOICE:
            return Invoice.objects.filter(branch=branch).count()
        if kind == DocumentSequence.KIND_QUOTATION:
            return Quotation.objects.filter(branch=branch).count()
        return 0

    @staticmethod
    @transaction.atomic
    def allocate(
        *,
        branch: Branch,
        kind: str,
        width: int = 6,
        prefix: str | None = None,
    ) -> dict:
        """Increment and return the next serial for this branch + kind.

        Returns ``{"number": "OSL-000001", "serial": 1, "kind": "...", "total_issued": 1}``.
        ``total_issued`` equals the serial and is the count of numbers generated so far.
        """
        if kind not in dict(DocumentSequence.KIND_CHOICES):
            raise ValueError(f"Unknown document sequence kind: {kind}")

        try:
            seq = DocumentSequence.objects.select_for_update().get(
                branch=branch, kind=kind, deleted_at__isnull=True
            )
        except DocumentSequence.DoesNotExist:
            seed = DocumentSequenceService._seed_value(branch=branch, kind=kind)
            try:
                seq = DocumentSequence.objects.create(
                    branch=branch,
                    kind=kind,
                    last_value=seed,
                )
            except IntegrityError:
                seq = DocumentSequence.objects.select_for_update().get(
                    branch=branch, kind=kind, deleted_at__isnull=True
                )

        seq.last_value += 1
        seq.save(update_fields=["last_value", "updated_at"])

        code_prefix = prefix
        if code_prefix is None:
            base = DocumentSequenceService.PREFIX.get(kind, "DOC")
            if kind in (DocumentSequence.KIND_INVOICE, DocumentSequence.KIND_QUOTATION):
                code_prefix = f"{base}-{branch.code}"
            else:
                code_prefix = base

        serial = seq.last_value
        number = f"{code_prefix}-{serial:0{width}d}"
        return {
            "number": number,
            "serial": serial,
            "kind": kind,
            "total_issued": serial,
            "branch_id": str(branch.id),
            "branch_code": branch.code,
        }

    @staticmethod
    def peek(*, branch: Branch, kind: str) -> dict:
        """Current count without allocating a new number."""
        seq = DocumentSequence.objects.filter(
            branch=branch, kind=kind, deleted_at__isnull=True
        ).first()
        total = (
            seq.last_value
            if seq
            else DocumentSequenceService._seed_value(branch=branch, kind=kind)
        )
        return {
            "kind": kind,
            "total_issued": total,
            "next_serial": total + 1,
            "branch_id": str(branch.id),
            "branch_code": branch.code,
        }
