"""School-scoped operational AR and posted-ledger reconciliation as of a date."""
from decimal import Decimal
from django.db.models import Q,Sum
from django.utils import timezone
from rest_framework import serializers
from apps.school.models.fees import SchoolInvoiceLink
from apps.sales.models.billing import ServiceInvoice,BillingAllocation,BillingCredit,BillingReceipt,BillingRefund
from apps.finance.models import JournalLine,CostCenter,BusinessUnit
from apps.sales.services import billing_service as billing


def summary(access,params):
    access.require('fee_finance','view');billing.require(access,write=False)
    day=serializers.DateField().run_validation(params.get('as_of') or str(timezone.localdate()))
    if day>timezone.localdate():billing.fail('As-of date cannot be in the future.')
    branch=access.campus(serializers.UUIDField().run_validation(params.get('branch_id')))
    dims={}
    for key,model in [('cost_center_id',CostCenter),('business_unit_id',BusinessUnit)]:
        if params.get(key):dims[key]=billing.get(access,model,params[key]).pk
    headers=ServiceInvoice.objects.filter(tenant=access.tenant,branch=branch,source_module='school',invoice__issue_date__lte=day,**dims).select_related('invoice__customer','receivable_account').order_by('invoice__due_date','invoice_id')
    # Journal source and campus/dimensions match the operational population; never compare tenant-wide retail AR.
    all_headers=ServiceInvoice.objects.filter(tenant=access.tenant,branch=branch,source_module='school')
    accounts=set(all_headers.values_list('receivable_account_id',flat=True))
    ledger=JournalLine.objects.filter(entry__tenant=access.tenant,entry__source_module='school',entry__status='posted',entry__entry_date__lte=day,entry__deleted_at__isnull=True,branch=branch,account_id__in=accounts,deleted_at__isnull=True,**dims)
    gl={str(r['account_id']):(r['d'] or 0)-(r['c'] or 0) for r in ledger.values('account_id').annotate(d=Sum('debit'),c=Sum('credit'))}
    op={};outstanding=[];totals={'invoiced':Decimal(0),'allocated':Decimal(0),'credits':Decimal(0),'outstanding':Decimal(0)}
    allocations=BillingAllocation.objects.filter(tenant=access.tenant,branch=branch,date__lte=day).filter(Q(reversal_date__isnull=True)|Q(reversal_date__gt=day))
    paid={r['invoice_id']:r['n'] for r in allocations.values('invoice_id').annotate(n=Sum('amount'))}
    credits={r['invoice_id']:r['n'] for r in BillingCredit.objects.filter(tenant=access.tenant,branch=branch,date__lte=day).filter(Q(reversal_date__isnull=True)|Q(reversal_date__gt=day)).values('invoice_id').annotate(n=Sum('amount'))}
    for h in headers:
        inv=h.invoice;p=paid.get(inv.pk,Decimal(0));c=credits.get(inv.pk,Decimal(0));due=inv.total_amount-p-c
        key=str(h.receivable_account_id);op[key]=op.get(key,Decimal(0))+due
        for name,value in [('invoiced',inv.total_amount),('allocated',p),('credits',c),('outstanding',due)]:totals[name]+=value
        if due:outstanding.append({'invoice_id':str(inv.pk),'number':inv.invoice_number,'customer':inv.customer.full_name,'due_date':str(inv.due_date),'balance':str(due),'overdue_days':max(0,(day-inv.due_date).days) if inv.due_date else 0})
    page=serializers.IntegerField(min_value=1).run_validation(params.get('page',1));size=serializers.IntegerField(min_value=1,max_value=100).run_validation(params.get('page_size',20))
    reconciliation=[{'account_id':key,'operational':str(op.get(key,Decimal(0))),'ledger':str(gl.get(key,Decimal(0))),'difference':str(op.get(key,Decimal(0))-gl.get(key,Decimal(0)))} for key in sorted(set(op)|set(gl))]
    receipts=BillingReceipt.objects.filter(tenant=access.tenant,branch=branch,received_date__lte=day,**dims).filter(Q(reversal_date__isnull=True)|Q(reversal_date__gt=day))
    advance=billing.sum_rows(receipts)-billing.sum_rows(allocations.filter(receipt__in=receipts))-billing.sum_rows(BillingRefund.objects.filter(receipt__in=receipts,date__lte=day).filter(Q(reversal_date__isnull=True)|Q(reversal_date__gt=day)))
    return {'currency':access.tenant.currency,'as_of':str(day),'branch_id':str(branch.pk),'totals':{k:str(v) for k,v in totals.items()},'unallocated_advances':str(advance),'reconciliation':reconciliation,'reconciled':all(Decimal(r['difference'])==0 for r in reconciliation),'outstanding':outstanding[(page-1)*size:page*size],'count':len(outstanding),'page':page,'page_size':size,'total_pages':max(1,(len(outstanding)+size-1)//size)}
