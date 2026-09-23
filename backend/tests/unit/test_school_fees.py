"""Phase 6 financial cycle, isolation and preservation gates."""
import pytest
from decimal import Decimal
from rest_framework.exceptions import ValidationError,PermissionDenied,NotFound
from tests.unit.test_school_sis import school_catalog,school,sis,direct
from apps.school.services.sis_crud import StudentCrudService as Crud
from apps.school.services.fee_crud import FeeCrud
from apps.school.services import fee_generation as fees
from apps.school.services.fee_reads import summary
from apps.sales.services import billing_service as billing
from apps.sales.models import Invoice,Payment
from apps.sales.models.billing import *
from apps.school.models.fees import *
from apps.finance.models import Account,AccountMapping,JournalEntry,JournalLine,CostCenter,BusinessUnit
from apps.finance.services.chart_service import ChartService
from apps.finance.services.posting_service import AccountingPostingService
pytestmark=pytest.mark.django_db

@pytest.fixture
def fee(sis,monkeypatch):
    from datetime import date
    monkeypatch.setattr('django.utils.timezone.localdate',lambda *args,**kwargs:date(2026,9,21))
    s=sis;ChartService.ensure_default_chart(tenant_id=s['t'].pk,user=s['owner'])
    for key,code in [('SCHOOL_ACCOUNTS_RECEIVABLE','1100'),('SCHOOL_ADVANCES','2200'),('SCHOOL_SCHOLARSHIP_DISCOUNT','6090'),('SCHOOL_TUITION_REVENUE','4000'),('SCHOOL_CASH','1000')]:
        AccountMapping.objects.create(tenant=s['t'],mapping_key=key,account=Account.objects.get(tenant=s['t'],code=code))
    cc=CostCenter.objects.create(tenant=s['t'],code='SCH',name='Campus');bu=BusinessUnit.objects.create(tenant=s['t'],code='SCHOOL',name='School')
    def create(resource,**data):return Crud.save(resource,data,access=s['access'])
    s['create']=create;b=str(s['a'].pk)
    s['settings']=create('fee-settings',branch_id=b,cost_center_id=str(cc.pk),business_unit_id=str(bu.pk))
    s['customer']=create('billing-customers',branch_id=b,customer_code='FAMILY',full_name='Family payer')
    s['method']=create('billing-methods',branch_id=b,code='CASH',name='Cash',account_mapping_key='SCHOOL_CASH')
    s['category']=create('fee-categories',branch_id=b,name='Tuition',code='TUITION',revenue_mapping_key='SCHOOL_TUITION_REVENUE')
    s['structure']=create('fee-structures',branch_id=b,name='Grade fees',academic_year_id=str(s['y'].pk),school_class_id=str(s['k'].pk))
    s['line']=create('fee-lines',structure_id=str(s['structure'].pk),category_id=str(s['category'].pk),period_key='2026-T1',amount='100.00',due_date='2026-09-15')
    FeeCrud.action('fee-structures',s['structure'].pk,'activate',{},access=s['access'])
    s['student']=direct(s);s['enrollment']=s['student'].enrollments.get()
    s['request']={'structure_id':str(s['structure'].pk),'issue_date':'2026-09-10','students':[{'enrollment_id':str(s['enrollment'].pk),'customer_id':str(s['customer'].pk)}]}
    return s

def issue(s):
    batch=fees.preview(s['request'],access=s['access']);fees.issue(batch.pk,{'fingerprint':batch.fingerprint},access=s['access']);return Invoice.objects.get(service_billing__isnull=False)

def receipt(s,amount='150',key='receipt-0001',day='2026-09-11'):
    return billing.collect({'customer_id':str(s['customer'].pk),'method_id':str(s['method'].pk),'amount':amount,'date':day,'idempotency_key':key},access=s['access'],settings=s['settings'])

def allocate(s,r,inv,amount='60',key='allocation-0001',day='2026-09-12'):
    return billing.allocate({'receipt_id':str(r.pk),'invoice_id':str(inv.pk),'amount':amount,'date':day,'idempotency_key':key},access=s['access'])

def report(s,day='2026-09-21',**extra):return summary(s['access'],{'branch_id':str(s['a'].pk),'as_of':day,**extra})

def test_fee_discount_receipt_advance_and_reconciliation(fee):
    s=fee;d=s['create']('fee-discounts',enrollment_id=str(s['enrollment'].pk),line_id=str(s['line'].pk),kind='percentage',value='25',reason='Approved scholarship')
    FeeCrud.action('fee-discounts',d.pk,'approve',{},access=s['access'])
    inv=issue(s);assert inv.total_amount==75 and inv.discount_amount==25 and inv.items.count()==0 and inv.service_lines.count()==1
    assert not Payment.objects.exists()
    assert AccountingPostingService.post_sale(invoice=inv,user=s['owner']).pk==inv.service_billing.journal_id
    assert JournalEntry.objects.filter(source_module='school').count()==1
    r=receipt(s);a=allocate(s,r,inv);inv.refresh_from_db();assert inv.amount_paid==60 and billing.balance(inv)==15 and billing.available(r)==90
    result=report(s);assert result['reconciled'] and Decimal(result['totals']['outstanding'])==15 and Decimal(result['unallocated_advances'])==90
    assert Decimal(report(s,'2026-09-10')['totals']['outstanding'])==75
    assert Decimal(report(s,'2026-09-11')['unallocated_advances'])==150
    for entry in JournalEntry.objects.filter(source_module='school'):
        lines=list(entry.lines.all());assert sum(l.debit for l in lines)==sum(l.credit for l in lines)
        assert all(l.branch_id==s['a'].pk and l.cost_center_id==s['settings'].cost_center_id and l.business_unit_id==s['settings'].business_unit_id for l in lines)

def test_idempotency_stale_preview_and_duplicate_charge(fee):
    s=fee;b=fees.preview(s['request'],access=s['access'])
    s['customer'].full_name='Renamed';s['customer'].save()
    with pytest.raises(ValidationError):fees.issue(b.pk,{'fingerprint':b.fingerprint},access=s['access'])
    b=fees.preview(s['request'],access=s['access'])
    for _ in range(2):fees.issue(b.pk,{'fingerprint':b.fingerprint},access=s['access'])
    assert Invoice.objects.count()==1 and StudentFeeAssignment.objects.count()==1
    with pytest.raises(ValidationError):fees.preview(s['request'],access=s['access'])
    r=receipt(s);assert receipt(s).pk==r.pk
    with pytest.raises(ValidationError):receipt(s,'200')
    inv=Invoice.objects.get();a=allocate(s,r,inv);assert allocate(s,r,inv).pk==a.pk
    with pytest.raises(ValidationError):allocate(s,r,inv,'41','other-allocation')

def test_credit_refund_reversal_history_and_dimensions(fee):
    s=fee;inv=issue(s);r=receipt(s);a=allocate(s,r,inv,'100')
    billing.reverse_allocation(a.pk,{'reason':'Correct allocation'},access=s['access']);inv.refresh_from_db();assert billing.balance(inv)==100
    credit=billing.credit({'invoice_line_id':str(inv.service_lines.get().pk),'amount':'40','date':'2026-09-21','reason':'Approved fee reduction','idempotency_key':'credit-0001'},access=s['access'])
    refund=billing.refund({'receipt_id':str(r.pk),'amount':'40','date':'2026-09-21','reason':'Return advance','idempotency_key':'refund-0001'},access=s['access'])
    assert billing.available(r)==110
    assert report(s)['reconciled'] and Decimal(report(s)['totals']['outstanding'])==60
    assert Decimal(report(s,'2026-09-12')['totals']['outstanding'])==0
    a.refresh_from_db();assert set(a.reversal.lines.values_list('cost_center_id',flat=True))=={s['settings'].cost_center_id}
    assert set(a.reversal.lines.values_list('business_unit_id',flat=True))=={s['settings'].business_unit_id}
    with pytest.raises(ValidationError):billing.reverse_receipt(r.pk,{'reason':'Cannot reverse refunded cash'},access=s['access'])
    fresh=receipt(s,'25','receipt-0002');billing.reverse_receipt(fresh.pk,{'reason':'Duplicate receipt'},access=s['access']);fresh.refresh_from_db();assert billing.available(fresh)==0
    assert billing.reverse_receipt(fresh.pk,{'reason':'Duplicate receipt'},access=s['access']).reversal_id==fresh.reversal_id

def test_legacy_mutations_and_nonstock_inventory(fee,monkeypatch):
    from apps.sales.services.sales_service import InvoiceService
    from apps.inventory.services.inventory_service import InventoryService
    from apps.sales.services.refund_service import RefundService
    s=fee
    def forbidden(*args,**kwargs):raise AssertionError('Tuition touched inventory')
    monkeypatch.setattr(InventoryService,'apply_invoice_quantity_deltas',forbidden)
    inv=issue(s)
    for fn,kwargs in [(InvoiceService.update,{'data':{}}),(InvoiceService.delete,{}),(InvoiceService.mark_paid,{}),(InvoiceService.mark_unpaid,{})]:
        with pytest.raises(ValueError):fn(instance=inv,user=s['owner'],**kwargs)
    from apps.sales.serializers.sales_serializers import serialize_invoice
    assert serialize_invoice(inv,include_items=True)['items'][0]['line_type']=='service'

def test_closed_period_disabled_accounting_and_atomic_rollback(fee,settings,monkeypatch):
    from datetime import date
    from apps.finance.services.period_service import PeriodService
    s=fee;batch=fees.preview(s['request'],access=s['access']);settings.ACCOUNTING_ENGINE_ENABLED=False
    with pytest.raises(ValidationError):fees.issue(batch.pk,{'fingerprint':batch.fingerprint},access=s['access'])
    assert not Invoice.objects.exists()
    settings.ACCOUNTING_ENGINE_ENABLED=True
    period=PeriodService.resolve(tenant_id=s['t'].pk,on_date=date(2026,9,10),user=s['owner']);period.status='closed';period.save()
    with pytest.raises(ValidationError):fees.issue(batch.pk,{'fingerprint':batch.fingerprint},access=s['access'])
    assert not Invoice.objects.exists() and not StudentFeeAssignment.objects.exists()
    period.status='open';period.save()
    original=billing.post
    def fail_post(*args,**kwargs):raise RuntimeError('Posting unavailable')
    monkeypatch.setattr(billing,'post',fail_post)
    with pytest.raises(RuntimeError):fees.issue(batch.pk,{'fingerprint':batch.fingerprint},access=s['access'])
    assert not Invoice.objects.exists() and not ServiceInvoiceLine.objects.exists()
    monkeypatch.setattr(billing,'post',original);fees.issue(batch.pk,{'fingerprint':batch.fingerprint},access=s['access'])
    monkeypatch.setattr(billing,'post',fail_post)
    with pytest.raises(RuntimeError):receipt(s)
    assert not BillingReceipt.objects.exists()

@pytest.mark.parametrize('value',['-1','0','NaN','Infinity','1.001'])
def test_receipt_amount_validation(fee,value):
    with pytest.raises(ValidationError):receipt(fee,value)
    assert not BillingReceipt.objects.exists()

def test_scholarship_rounding_full_waiver_and_rejected_discount(fee):
    s=fee;s['line'].amount=Decimal('0.05');s['line'].save()
    d=s['create']('fee-discounts',enrollment_id=str(s['enrollment'].pk),line_id=str(s['line'].pk),kind='percentage',value='50',reason='Half scholarship')
    FeeCrud.action('fee-discounts',d.pk,'approve',{},access=s['access']);inv=issue(s);assert inv.total_amount==Decimal('.02') and inv.discount_amount==Decimal('.03')
    with pytest.raises(ValidationError):Crud.save('fee-discounts',{'value':'20'},pk=d.pk,access=s['access'])

def test_zero_fee_has_no_spurious_journal(fee):
    s=fee;d=s['create']('fee-discounts',enrollment_id=str(s['enrollment'].pk),line_id=str(s['line'].pk),kind='percentage',value='100',reason='Full scholarship');FeeCrud.action('fee-discounts',d.pk,'approve',{},access=s['access']);inv=issue(s)
    assert inv.total_amount==0 and inv.status=='paid' and inv.service_billing.journal_id is None
    assert not JournalEntry.objects.filter(source_module='school').exists() and report(s)['reconciled']

def test_shared_permission_and_campus_boundaries(fee):
    from apps.authentication.models import Permission,Role,RolePermission
    from apps.school.repositories.sis import StudentAccess
    s=fee;inv=issue(s)
    s['client'].force_authenticate(s['u'])
    assert s['client'].get('/api/v1/school/sis/billing-invoices/').status_code==403
    role=s['u'].role
    for permission in Permission.objects.filter(codename__in=['finance.view','finance.create','finance.approve','sales.create','customers.view']):RolePermission.objects.get_or_create(role=role,permission=permission)
    s['client'].force_authenticate(s['u'])
    customer=s['create']('billing-customers',branch_id=str(s['b'].pk),customer_code='OTHER',full_name='Other campus')
    assert s['client'].get(f'/api/v1/school/sis/billing-customers/{customer.pk}/').status_code==404
    bad={**s['request'],'students':[{'enrollment_id':str(s['enrollment'].pk),'customer_id':str(customer.pk)}]}
    with pytest.raises(ValidationError):fees.preview(bad,access=s['access'])
    s['client'].force_authenticate(s['foreign']);assert s['client'].get(f'/api/v1/school/sis/billing-invoices/{inv.pk}/').status_code in (403,404)
    s['client'].force_authenticate(s['owner'])
    assert s['client'].patch(f'/api/v1/school/sis/billing-invoices/{inv.pk}/',{'amount_paid':'100'},format='json').status_code in (400,403)
    assert s['client'].delete(f'/api/v1/school/sis/billing-invoices/{inv.pk}/').status_code==400


def test_multiple_invoices_allocation_and_refund_bounds(fee):
    s=fee;student=direct(s,first_name='Sibling');s['request']['students'].append({'enrollment_id':str(student.enrollments.get().pk),'customer_id':str(s['customer'].pk)})
    batch=fees.preview(s['request'],access=s['access']);fees.issue(batch.pk,{'fingerprint':batch.fingerprint},access=s['access']);invoices=list(Invoice.objects.all());r=receipt(s)
    allocate(s,r,invoices[0],'100');allocate(s,r,invoices[1],'50','allocation-0002')
    assert billing.available(r)==0 and Decimal(report(s)['totals']['outstanding'])==50
    with pytest.raises(ValidationError):allocate(s,r,invoices[1],'1','allocation-0003')
    with pytest.raises(ValidationError):billing.refund({'receipt_id':str(r.pk),'amount':'1','date':'2026-09-21','reason':'Over refund','idempotency_key':'over-refund-1'},access=s['access'])
    assert not BillingRefund.objects.exists()

def test_deferred_revenue_and_credit_policy(fee):
    s=fee;s['category'].recognition='deferred';s['category'].revenue_mapping_key='SCHOOL_ADVANCES';s['category'].save();inv=issue(s)
    assert inv.service_billing.journal.lines.filter(account__account_type='liability',credit=100).exists()
    billing.credit({'invoice_line_id':str(inv.service_lines.get().pk),'amount':'25','date':'2026-09-21','reason':'Reduce deferred charge','idempotency_key':'deferred-credit'},access=s['access'])
    assert BillingCredit.objects.get().journal.lines.filter(account__account_type='liability',debit=25).exists()
    assert report(s)['reconciled']

def test_mapping_failure_and_no_generic_backfill(fee):
    from apps.finance.services.backfill_service import AccountingBackfillService
    s=fee;AccountMapping.objects.filter(tenant=s['t'],mapping_key='SCHOOL_TUITION_REVENUE').update(is_active=False)
    with pytest.raises(ValidationError):fees.preview(s['request'],access=s['access'])
    AccountMapping.objects.filter(tenant=s['t'],mapping_key='SCHOOL_TUITION_REVENUE').update(is_active=True);inv=issue(s)
    data=AccountingBackfillService.preview(tenant_id=s['t'].pk)
    assert str(inv.pk) not in str(data['missing']['invoices'])
    assert not JournalLine.objects.filter(entry__source_module='school',account__code__in=['5000','1200']).exists()

def test_dimension_filters_and_pagination(fee):
    s=fee;issue(s);assert report(s,cost_center_id=str(s['settings'].cost_center_id))['reconciled']
    other=CostCenter.objects.create(tenant=s['t'],code='OTHER',name='Other')
    result=report(s,cost_center_id=str(other.pk));assert result['count']==0 and result['reconciled']
    with pytest.raises(ValidationError):report(s,page_size=101)

def test_adjustment_reversals_and_central_bypass_guard(fee):
    from apps.finance.services.reversal_service import AccountingReversalService,ReversalError
    s=fee;inv=issue(s);r=receipt(s)
    c=billing.credit({'invoice_line_id':str(inv.service_lines.get().pk),'amount':'30','date':'2026-09-15','reason':'Approved adjustment','idempotency_key':'credit-to-reverse'},access=s['access'])
    f=billing.refund({'receipt_id':str(r.pk),'amount':'20','date':'2026-09-15','reason':'Approved refund','idempotency_key':'refund-to-reverse'},access=s['access'])
    with pytest.raises(ReversalError):AccountingReversalService.reverse_entry(entry=c.journal,user=s['owner'],reason='Bypass billing')
    for model,row in [(BillingCredit,c),(BillingRefund,f)]:
        reversed_row=billing.reverse_adjustment(model,row.pk,{'reason':'Correct duplicate adjustment'},access=s['access'])
        assert billing.reverse_adjustment(model,row.pk,{'reason':'Retry adjustment reversal'},access=s['access']).reversal_id==reversed_row.reversal_id
    inv.refresh_from_db();assert billing.balance(inv)==100 and billing.available(r)==150
    assert Decimal(report(s,'2026-09-15')['totals']['outstanding'])==70
    assert report(s)['reconciled'] and Decimal(report(s)['totals']['outstanding'])==100


def test_unbalanced_posting_rejected_without_partial_state(fee,monkeypatch):
    s=fee;original=AccountingPostingService._build_lines
    def broken(**kwargs):
        lines,description,day=original(**kwargs);lines[0]['debit']='1';return lines,description,day
    monkeypatch.setattr(AccountingPostingService,'_build_lines',broken)
    with pytest.raises(ValidationError):issue(s)
    assert not Invoice.objects.exists() and not JournalEntry.objects.filter(source_module='school').exists()

def test_reversal_closed_period_and_long_audit_reason(fee):
    from datetime import date
    from apps.finance.services.period_service import PeriodService
    s=fee;r=receipt(s);period=PeriodService.resolve(tenant_id=s['t'].pk,on_date=date(2026,9,21),user=s['owner']);period.status='closed';period.save()
    with pytest.raises(ValidationError):billing.reverse_receipt(r.pk,{'reason':'Period is closed'},access=s['access'])
    r.refresh_from_db();assert r.reversal_id is None
    period.status='open';period.save();row=billing.reverse_receipt(r.pk,{'reason':'Approved correction. '*50},access=s['access'])
    assert len(row.reversal.description)<=255 and len(row.reversal.notes)>255

def test_backdated_commands_cannot_overallocate_history_after_reversal(fee):
    s=fee;inv=issue(s);r=receipt(s,'100');a=allocate(s,r,inv,'100');billing.reverse_allocation(a.pk,{'reason':'Correct allocation'},access=s['access'])
    with pytest.raises(ValidationError):allocate(s,r,inv,'100','backdated-allocation','2026-09-13')
    with pytest.raises(ValidationError):billing.credit({'invoice_line_id':str(inv.service_lines.get().pk),'amount':'25','date':'2026-09-13','reason':'Backdated credit','idempotency_key':'backdated-credit'},access=s['access'])
    with pytest.raises(ValidationError):billing.refund({'receipt_id':str(r.pk),'amount':'25','date':'2026-09-13','reason':'Backdated refund','idempotency_key':'backdated-refund'},access=s['access'])
    allocate(s,r,inv,'100','replacement-allocation','2026-09-21')
    assert report(s)['reconciled'] and report(s,'2026-09-13')['reconciled']
