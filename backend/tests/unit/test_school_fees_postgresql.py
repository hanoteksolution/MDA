"""Real PostgreSQL races and upgrade preservation for Phase 6 shared billing."""
import pytest
from django.db import connection
from tests.unit.test_school_fees import school_catalog,school,sis,fee
from tests.unit.test_school_postgresql import race
from apps.school.services import fee_generation as fees
from apps.sales.models import Invoice,Payment
from apps.sales.models.billing import BillingReceipt,BillingAllocation,BillingRefund,BillingCredit
from apps.finance.models import JournalEntry
pytestmark=pytest.mark.django_db(transaction=True)

@pytest.fixture(autouse=True)
def require_postgres():
    if connection.vendor!='postgresql':pytest.skip('PostgreSQL transaction/migration gate.')

def test_fee_receipt_allocation_refund_credit_races(fee):
    s=fee;url='/api/v1/school/sis/'
    batches=[fees.preview(s['request'],access=s['access']) for _ in range(2)]
    r=race(s['owner'],[(url+f'fee-batches/{b.pk}/issue/',{'fingerprint':b.fingerprint}) for b in batches]);assert sorted(code for code,_ in r)==[200,400],r
    inv=Invoice.objects.get();assert JournalEntry.objects.filter(source_module='school').count()==1
    receipt={'branch_id':str(s['a'].pk),'customer_id':str(s['customer'].pk),'method_id':str(s['method'].pk),'amount':'100','date':'2026-09-11','idempotency_key':'concurrent-receipt'}
    r=race(s['owner'],[(url+'billing-receipts/',receipt)]*2);assert [code for code,_ in r]==[201,201],r
    assert BillingReceipt.objects.count()==1;received=BillingReceipt.objects.get()
    alloc={'receipt_id':str(received.pk),'invoice_id':str(inv.pk),'amount':'80','date':'2026-09-12'}
    r=race(s['owner'],[(url+'billing-allocations/',{**alloc,'idempotency_key':key}) for key in ['allocation-race1','allocation-race2']]);assert sorted(code for code,_ in r)==[201,400],r
    assert BillingAllocation.objects.count()==1
    refund={'receipt_id':str(received.pk),'amount':'15','date':'2026-09-15','reason':'Approved refund'}
    r=race(s['owner'],[(url+'billing-refunds/',{**refund,'idempotency_key':key}) for key in ['refund-race1','refund-race2']]);assert sorted(code for code,_ in r)==[201,400],r
    assert BillingRefund.objects.count()==1
    allocation=BillingAllocation.objects.get()
    r=race(s['owner'],[(url+f'billing-allocations/{allocation.pk}/reverse/',{'reason':'Approved correction'})]*2);assert [code for code,_ in r]==[200,200],r
    assert JournalEntry.objects.filter(reverses_entry=allocation.journal).count()==1
    credit={'invoice_line_id':str(inv.service_lines.get().pk),'amount':'80','date':'2026-09-21','reason':'Approved reduction'}
    r=race(s['owner'],[(url+'billing-credits/',{**credit,'idempotency_key':key}) for key in ['credit-race1','credit-race2']]);assert sorted(code for code,_ in r)==[201,400],r
    assert BillingCredit.objects.count()==1 and not Payment.objects.exists()


def test_upgrade_preserves_legacy_tender_and_reverse_when_empty():
    from django.db.migrations.executor import MigrationExecutor
    executor=MigrationExecutor(connection);latest=executor.loader.graph.leaf_nodes();previous=[('school','0008_phase5_ranking'),('sales','0010_backfill_default_terminals')]
    try:
        executor.migrate(previous);apps=MigrationExecutor(connection).loader.project_state(previous).apps
        tenant=apps.get_model('platform','Tenant').objects.create(name='Legacy billing',slug='phase6-legacy')
        company=apps.get_model('settings_app','Company').objects.create(tenant_id=tenant.pk,name='Legacy')
        branch=apps.get_model('settings_app','Branch').objects.create(tenant_id=tenant.pk,company_id=company.pk,name='Legacy',code='LEG')
        customer=apps.get_model('customers','Customer').objects.create(tenant_id=tenant.pk,branch_id=branch.pk,customer_code='LEG',full_name='Legacy payer')
        inv=apps.get_model('sales','Invoice').objects.create(tenant_id=tenant.pk,branch_id=branch.pk,customer_id=customer.pk,invoice_number='LEG-1',total_amount=10,amount_paid=10,status='paid')
        tender=apps.get_model('sales','Payment').objects.create(tenant_id=tenant.pk,branch_id=branch.pk,invoice_id=inv.pk,method='cash',amount=10)
        student=apps.get_model('school','Student').objects.create(tenant_id=tenant.pk,branch_id=branch.pk,number='S-1',first_name='Preserved',date_of_birth='2015-01-01',admission_date='2026-09-01')
        MigrationExecutor(connection).migrate(latest)
        assert Payment.objects.get(pk=tender.pk).amount==10 and Invoice.objects.get(pk=inv.pk).amount_paid==10
        assert not BillingReceipt.objects.exists()
        MigrationExecutor(connection).migrate(previous);old=MigrationExecutor(connection).loader.project_state(previous).apps
        assert old.get_model('sales','Payment').objects.filter(pk=tender.pk).exists()
        assert old.get_model('school','Student').objects.filter(pk=student.pk).exists()
    finally:MigrationExecutor(connection).migrate(latest)
