"""Additive non-stock invoicing and economic receipts; legacy tenders are unchanged."""
from django.db import models
from django.db.models import Q
from core.models.base import BaseModel


def ref(model, **kwargs):return models.ForeignKey(model,on_delete=models.PROTECT,**kwargs)
def money(**kwargs):return models.DecimalField(max_digits=18,decimal_places=2,**kwargs)

class BillingRecord(BaseModel):
    tenant=ref('platform.Tenant')
    branch=ref('settings_app.Branch')
    class Meta:abstract=True

class BillingMethod(BillingRecord):
    code=models.CharField(max_length=30)
    name=models.CharField(max_length=100)
    account_mapping_key=models.CharField(max_length=50)
    is_active=models.BooleanField(default=True)
    class Meta:constraints=[models.UniqueConstraint(fields=['tenant','branch','code'],name='billing_method_code')]
    def __str__(self):return self.name

class ServiceInvoice(BillingRecord):
    invoice=models.OneToOneField('sales.Invoice',on_delete=models.PROTECT,related_name='service_billing')
    source_module=models.CharField(max_length=30)
    receivable_account=ref('finance.Account',related_name='+')
    credit_account=ref('finance.Account',related_name='+')
    cost_center=ref('finance.CostCenter',null=True,blank=True)
    business_unit=ref('finance.BusinessUnit',null=True,blank=True)
    journal=ref('finance.JournalEntry',null=True,blank=True)
    class Meta:constraints=[models.UniqueConstraint(fields=['tenant','invoice'],name='billing_service_invoice')]

class ServiceInvoiceLine(BillingRecord):
    invoice=ref('sales.Invoice',related_name='service_lines')
    description=models.CharField(max_length=200)
    gross_amount=money()
    discount_amount=money(default=0)
    amount=money()
    revenue_account=ref('finance.Account')
    class Meta:constraints=[models.CheckConstraint(condition=Q(amount__gte=0,gross_amount__gte=0,discount_amount__gte=0),name='billing_service_line_nonnegative')]

class BillingReceipt(BillingRecord):
    customer=ref('customers.Customer')
    method=ref(BillingMethod)
    source_module=models.CharField(max_length=30,default='school')
    amount=money()
    received_date=models.DateField()
    reference=models.CharField(max_length=100,blank=True)
    idempotency_key=models.CharField(max_length=64)
    request_hash=models.CharField(max_length=64)
    cash_account=ref('finance.Account',related_name='+')
    advance_account=ref('finance.Account',related_name='+')
    cost_center=ref('finance.CostCenter',null=True,blank=True)
    business_unit=ref('finance.BusinessUnit',null=True,blank=True)
    status=models.CharField(max_length=20,default='posted')
    journal=ref('finance.JournalEntry',null=True,blank=True,related_name='+')
    reversal=ref('finance.JournalEntry',null=True,blank=True,related_name='+')
    reversal_date=models.DateField(null=True,blank=True)
    reason=models.TextField(blank=True)
    class Meta:constraints=[models.UniqueConstraint(fields=['tenant','idempotency_key'],name='billing_receipt_request'),models.CheckConstraint(condition=Q(amount__gt=0),name='billing_receipt_positive')]
    def __str__(self):return f'Receipt {str(self.pk)[:8]}'

class BillingAllocation(BillingRecord):
    receipt=ref(BillingReceipt,related_name='allocations')
    invoice=ref('sales.Invoice',related_name='billing_allocations')
    amount=money()
    date=models.DateField()
    idempotency_key=models.CharField(max_length=64)
    request_hash=models.CharField(max_length=64)
    journal=ref('finance.JournalEntry',null=True,blank=True,related_name='+')
    reversal=ref('finance.JournalEntry',null=True,blank=True,related_name='+')
    reversal_date=models.DateField(null=True,blank=True)
    reason=models.TextField(blank=True)
    class Meta:constraints=[models.UniqueConstraint(fields=['tenant','idempotency_key'],name='billing_allocation_request'),models.CheckConstraint(condition=Q(amount__gt=0),name='billing_allocation_positive')]

class BillingCredit(BillingRecord):
    invoice_line=ref(ServiceInvoiceLine,related_name='credits')
    invoice=ref('sales.Invoice',related_name='billing_credits')
    amount=money()
    date=models.DateField()
    reason=models.TextField()
    idempotency_key=models.CharField(max_length=64)
    request_hash=models.CharField(max_length=64)
    journal=ref('finance.JournalEntry',null=True,blank=True)
    reversal=ref('finance.JournalEntry',null=True,blank=True,related_name='+')
    reversal_date=models.DateField(null=True,blank=True)
    reversal_reason=models.TextField(blank=True)
    class Meta:constraints=[models.UniqueConstraint(fields=['tenant','idempotency_key'],name='billing_credit_request'),models.CheckConstraint(condition=Q(amount__gt=0),name='billing_credit_positive')]

class BillingRefund(BillingRecord):
    receipt=ref(BillingReceipt,related_name='refunds')
    amount=money()
    date=models.DateField()
    reason=models.TextField()
    idempotency_key=models.CharField(max_length=64)
    request_hash=models.CharField(max_length=64)
    journal=ref('finance.JournalEntry',null=True,blank=True)
    reversal=ref('finance.JournalEntry',null=True,blank=True,related_name='+')
    reversal_date=models.DateField(null=True,blank=True)
    reversal_reason=models.TextField(blank=True)
    class Meta:constraints=[models.UniqueConstraint(fields=['tenant','idempotency_key'],name='billing_refund_request'),models.CheckConstraint(condition=Q(amount__gt=0),name='billing_refund_positive')]
