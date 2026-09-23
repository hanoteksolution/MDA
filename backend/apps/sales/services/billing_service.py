"""Shared non-stock billing: atomic economic receipts and bounded allocations."""
import hashlib,json
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum,Max
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound,PermissionDenied,ValidationError
from apps.sales.models import Invoice,DocumentSequence
from apps.sales.models.billing import *
from apps.finance.services.posting_service import AccountingPostingService
from apps.finance.services.reversal_service import AccountingReversalService
from apps.finance.services.mapping_service import MappingService
from apps.finance.services.cutover_service import AccountingCutoverService
from apps.sales.services.sequence_service import DocumentSequenceService
from apps.audit.services import write_audit

ZERO=Decimal('0.00')
def fail(message):raise ValidationError({'billing':message})
def amount(value):return serializers.DecimalField(max_digits=18,decimal_places=2,min_value=Decimal('.01')).run_validation(value)
def digest(data):return hashlib.sha256(json.dumps(data,sort_keys=True,default=str).encode()).hexdigest()
def date(data,key='date'):
    value=serializers.DateField().run_validation(data.get(key))
    if value>timezone.localdate():fail('Future financial transactions are not supported.')
    return value

def require(access,write=True,approve=False):
    for code in (('finance.create','sales.create') if write else ('finance.view',)):
        if not access.user.has_permission(code):raise PermissionDenied(f'{code} permission is required.')
    if approve and not access.user.has_permission('finance.approve'):raise PermissionDenied('finance.approve permission is required.')
    if write and not AccountingCutoverService.is_posting_enabled(tenant_id=access.tenant.pk):fail('Accounting posting is disabled. No financial transaction was saved.')

def lock(access):type(access.tenant).objects.select_for_update().get(pk=access.tenant.pk)
def get(access,model,pk):
    pk=serializers.UUIDField().run_validation(pk)
    row=access.scope(model.objects.all()).filter(pk=pk,deleted_at__isnull=True).first()
    if row is None:raise NotFound('Billing record is outside your tenant/campus scope.')
    return row

def account(access,key,types):
    try:row=MappingService.resolve(key=key,tenant_id=access.tenant.pk,user=access.user)
    except ValueError as exc:fail(str(exc))
    if row.tenant_id!=access.tenant.pk or not row.is_active or row.deleted_at or row.account_type not in types:fail(f'Invalid or inactive account mapping: {key}.')
    return row

def save(row,access,action):
    row.created_by=row.created_by or access.user;row.updated_by=access.user
    row.full_clean();row.save()
    write_audit(module=row._meta.app_label,action=action,entity=row,user=access.user,request=access.request,new_values={'id':str(row.pk),'amount':str(getattr(row,'amount','')),'reason':getattr(row,'reason',''),'status':getattr(row,'status','')})
    return row

def replay(model,data,access):
    key=serializers.CharField(min_length=8,max_length=64).run_validation(data.get('idempotency_key'))
    old=model.objects.filter(tenant=access.tenant,idempotency_key=key).first()
    if old:
        access.campus(old.branch_id)
        if old.request_hash!=digest(data):fail('Idempotency key was already used with different inputs.')
    return key,old

def sum_rows(qs):return qs.aggregate(n=Sum('amount'))['n'] or ZERO

def available(receipt):
    if receipt.status!='posted':return ZERO
    return receipt.amount-sum_rows(receipt.allocations.filter(reversal__isnull=True))-sum_rows(receipt.refunds.filter(reversal__isnull=True))

def balance(invoice):return invoice.total_amount-invoice.amount_paid-sum_rows(invoice.billing_credits.filter(reversal__isnull=True))
def refresh_invoice(invoice):
    invoice.amount_paid=sum_rows(invoice.billing_allocations.filter(reversal__isnull=True))
    invoice.status=Invoice.STATUS_PAID if balance(invoice)==0 else Invoice.STATUS_SENT
    invoice.save(update_fields=['amount_paid','status','updated_at'])

def ordered_date(day,*records):
    # Backdating after a reversal must not recreate overallocated historical balances.
    for record in records:
        latest=record.received_date if isinstance(record,BillingReceipt) else record.issue_date
        groups=[record.allocations,record.refunds] if isinstance(record,BillingReceipt) else [record.billing_allocations,record.billing_credits]
        for group in groups:
            values=group.aggregate(activity=Max('date'),reversal=Max('reversal_date'))
            latest=max([latest]+[value for value in values.values() if value])
        if day<latest:fail('Transaction date precedes existing financial activity. Use that date or a later date to preserve historical balances.')


def dimensions(record):return {'cost_center_id':str(record.cost_center_id) if record.cost_center_id else None,'business_unit_id':str(record.business_unit_id) if record.business_unit_id else None}
def line(account_id,debit=ZERO,credit=ZERO,**dims):return {'account_id':str(account_id),'debit':str(debit),'credit':str(credit),**dims}

def post(record,access,event,lines,on_date,source_type='payment'):
    try:
        return AccountingPostingService.post(event_type=event,tenant_id=access.tenant.pk,source_module='school',source_type=source_type,source_id=record.invoice_id if isinstance(record,ServiceInvoice) else record.pk,payload={'entry_date':str(on_date),'description':event.replace('_',' ').title(),'lines':lines},idempotency_key=f'{event}:{record.pk}',user=access.user,branch_id=record.branch_id)
    except ValueError as exc:fail(str(exc))

@transaction.atomic
def issue_service_invoice(*,access,branch,customer,on_date,due_date,rows,settings,idempotency_key):
    require(access);lock(access);access.campus(branch.pk)
    if customer.tenant_id!=access.tenant.pk or customer.branch_id!=branch.pk or not customer.is_active or customer.deleted_at:fail('Choose an active billing customer in this campus.')
    ar=account(access,settings.receivable_mapping_key,('asset',));credit=account(access,settings.credit_mapping_key,('expense','revenue'))
    inv=Invoice.objects.filter(tenant=access.tenant,idempotency_key=idempotency_key).first()
    if inv:return inv
    inv=Invoice(tenant=access.tenant,branch=branch,customer=customer,created_by_user=access.user,invoice_number=DocumentSequenceService.allocate(branch=branch,kind=DocumentSequence.KIND_INVOICE)['number'],issue_date=on_date,due_date=due_date,status=Invoice.STATUS_SENT,idempotency_key=idempotency_key)
    inv.subtotal=sum((r['gross'] for r in rows),ZERO);inv.discount_amount=sum((r['discount'] for r in rows),ZERO);inv.total_amount=inv.subtotal-inv.discount_amount
    if inv.total_amount<0:fail('Net charge cannot be negative.')
    if inv.total_amount==0:inv.status=Invoice.STATUS_PAID
    save(inv,access,'service_invoice_issued')
    header=ServiceInvoice(tenant=access.tenant,branch=branch,invoice=inv,source_module='school',receivable_account=ar,credit_account=credit,cost_center=settings.cost_center,business_unit=settings.business_unit)
    save(header,access,'service_invoice_linked');dims=dimensions(header);lines=[line(ar.pk,debit=inv.total_amount,**dims)]
    for r in rows:
        item=ServiceInvoiceLine(tenant=access.tenant,branch=branch,invoice=inv,description=r['description'],gross_amount=r['gross'],discount_amount=r['discount'],amount=r['gross']-r['discount'],revenue_account=r['revenue'])
        save(item,access,'service_line_issued')
        if item.amount:lines.append(line(r['revenue'].pk,credit=item.amount,**dims))
    if inv.total_amount:header.journal=post(header,access,'SCHOOL_FEE_INVOICED',lines,on_date,'invoice')
    save(header,access,'service_invoice_posted' if inv.total_amount else 'zero_charge_recorded')
    return inv

@transaction.atomic
def collect(data,*,access,settings):
    require(access);lock(access);key,old=replay(BillingReceipt,data,access)
    if old:return old
    from apps.customers.models import Customer
    customer=get(access,Customer,data.get('customer_id'));method=get(access,BillingMethod,data.get('method_id'))
    if customer.branch_id!=settings.branch_id or method.branch_id!=settings.branch_id or not customer.is_active or not method.is_active:fail('Customer and active payment method must match this campus.')
    row=BillingReceipt(tenant=access.tenant,branch=settings.branch,customer=customer,method=method,amount=amount(data.get('amount')),received_date=date(data),reference=serializers.CharField(max_length=100,allow_blank=True).run_validation(data.get('reference','')),idempotency_key=key,request_hash=digest(data),cash_account=account(access,method.account_mapping_key,('asset',)),advance_account=account(access,settings.advance_mapping_key,('liability',)),cost_center=settings.cost_center,business_unit=settings.business_unit)
    save(row,access,'receipt_recorded');dims=dimensions(row)
    row.journal=post(row,access,'SCHOOL_FEE_PAYMENT',[line(row.cash_account_id,debit=row.amount,**dims),line(row.advance_account_id,credit=row.amount,**dims)],row.received_date)
    return save(row,access,'receipt_posted')

@transaction.atomic
def allocate(data,*,access):
    require(access);lock(access);key,old=replay(BillingAllocation,data,access)
    if old:return old
    receipt=get(access,BillingReceipt,data.get('receipt_id'));invoice=get(access,Invoice,data.get('invoice_id'))
    header=get(access,ServiceInvoice,getattr(getattr(invoice,'service_billing',None),'pk',None))
    value=amount(data.get('amount'));day=date(data)
    if invoice.branch_id!=receipt.branch_id or invoice.customer_id!=receipt.customer_id or header.source_module!=receipt.source_module:fail('Allocation must share campus, customer and source.')
    ordered_date(day,receipt,invoice)
    if day<max(invoice.issue_date,receipt.received_date):fail('Allocation predates invoice or receipt.')
    if value>available(receipt) or value>balance(invoice):fail('Allocation exceeds available receipt funds or outstanding invoice balance.')
    row=BillingAllocation(tenant=access.tenant,branch=invoice.branch,receipt=receipt,invoice=invoice,amount=value,date=day,idempotency_key=key,request_hash=digest(data))
    save(row,access,'allocation_recorded')
    row.journal=post(row,access,'SCHOOL_FEE_ALLOCATED',[line(receipt.advance_account_id,debit=value,**dimensions(receipt)),line(header.receivable_account_id,credit=value,**dimensions(header))],day)
    save(row,access,'allocation_posted');refresh_invoice(invoice);return row

def reverse_journal(entry,access,reason):
    try:return AccountingReversalService.reverse_entry(entry=entry,user=access.user,reason=reason,billing_workflow=True)
    except ValueError as exc:fail(str(exc))


@transaction.atomic
def reverse_allocation(pk,data,*,access):
    require(access,approve=True);lock(access);row=get(access,BillingAllocation,pk)
    why=serializers.CharField(min_length=3,max_length=2000).run_validation(data.get('reason'))
    if row.reversal_id:return row
    row.reversal=reverse_journal(row.journal,access,why);row.reversal_date=timezone.localdate();row.reason=why
    save(row,access,'allocation_reversed');refresh_invoice(row.invoice);return row

@transaction.atomic
def credit(data,*,access):
    require(access,approve=True);lock(access);key,old=replay(BillingCredit,data,access)
    if old:return old
    item=get(access,ServiceInvoiceLine,data.get('invoice_line_id'));invoice=get(access,Invoice,item.invoice_id);header=get(access,ServiceInvoice,getattr(getattr(invoice,'service_billing',None),'pk',None));value=amount(data.get('amount'));day=date(data)
    ordered_date(day,invoice)
    if value>item.amount-sum_rows(item.credits.filter(reversal__isnull=True)):fail('Credit exceeds the remaining charge on this line.')
    if value>balance(invoice) or day<invoice.issue_date:fail('Credit exceeds outstanding charges or predates the invoice; reverse allocations before crediting paid charges.')
    row=BillingCredit(tenant=access.tenant,branch=invoice.branch,invoice=invoice,invoice_line=item,amount=value,date=day,reason=serializers.CharField(min_length=3,max_length=2000).run_validation(data.get('reason')),idempotency_key=key,request_hash=digest(data));save(row,access,'credit_recorded');dims=dimensions(header)
    row.journal=post(row,access,'SCHOOL_FEE_CREDIT',[line(item.revenue_account_id if item.revenue_account.account_type=='liability' else header.credit_account_id,debit=value,**dims),line(header.receivable_account_id,credit=value,**dims)],day,'invoice');save(row,access,'credit_posted');refresh_invoice(invoice);return row

@transaction.atomic
def refund(data,*,access):
    require(access,approve=True);lock(access);key,old=replay(BillingRefund,data,access)
    if old:return old
    receipt=get(access,BillingReceipt,data.get('receipt_id'));value=amount(data.get('amount'));day=date(data)
    ordered_date(day,receipt)
    if value>available(receipt) or day<receipt.received_date:fail('Refund exceeds unallocated funds or predates receipt. Reverse allocations and credit charges separately when required.')
    row=BillingRefund(tenant=access.tenant,branch=receipt.branch,receipt=receipt,amount=value,date=day,reason=serializers.CharField(min_length=3,max_length=2000).run_validation(data.get('reason')),idempotency_key=key,request_hash=digest(data));save(row,access,'refund_recorded');dims=dimensions(receipt)
    row.journal=post(row,access,'SCHOOL_FEE_REFUND',[line(receipt.advance_account_id,debit=value,**dims),line(receipt.cash_account_id,credit=value,**dims)],day,'sale_refund');return save(row,access,'refund_posted')

@transaction.atomic
def reverse_receipt(pk,data,*,access):
    require(access,approve=True);lock(access);row=get(access,BillingReceipt,pk)
    why=serializers.CharField(min_length=3,max_length=2000).run_validation(data.get('reason'))
    if row.reversal_id:return row
    if available(row)!=row.amount:fail('Reverse allocations first; receipts with refunds cannot be reversed.')
    row.reversal=reverse_journal(row.journal,access,why);row.reversal_date=timezone.localdate();row.status='reversed';row.reason=why
    return save(row,access,'receipt_reversed')


@transaction.atomic
def reverse_adjustment(model,pk,data,*,access):
    require(access,approve=True);lock(access);row=get(access,model,pk)
    why=serializers.CharField(min_length=3,max_length=2000).run_validation(data.get('reason'))
    if row.reversal_id:return row
    row.reversal=reverse_journal(row.journal,access,why)
    row.reversal_date=timezone.localdate();row.reversal_reason=why
    save(row,access,'billing_adjustment_reversed')
    if isinstance(row,BillingCredit):refresh_invoice(row.invoice)
    return row
