"""Legacy interface shape checks (implementations live in STEP 11)."""

from decimal import Decimal
from uuid import uuid4

from apps.inventory.services.receiving_service import ReceiveLineInput
from apps.inventory.services.transfer_service import TransferLineInput


def test_transfer_line_input_shape():
    line = TransferLineInput(product_id=uuid4(), quantity=Decimal("2.5"))
    assert line.quantity == Decimal("2.5")


def test_receive_line_input_shape():
    line = ReceiveLineInput(product_id=uuid4(), quantity_received=Decimal("1"))
    assert line.quantity_received == Decimal("1")
