"""Human-readable billing records without editable balance fields."""
from apps.school.models.fees import SchoolInvoiceLink,FeeBatch,FeeStructureLine,FeeDiscount,StudentFeeAssignment
from apps.sales.models.billing import BillingReceipt,BillingAllocation,BillingCredit,BillingRefund,ServiceInvoiceLine
from apps.customers.models import Customer
from apps.sales.models import Invoice
from apps.sales.services.billing_service import available,balance

def augment(row,data):
    if isinstance(row,Invoice):data.update(name=row.invoice_number,customer_name=row.customer.full_name,balance=str(balance(row)),lines=[{'id':str(i.pk),'description':i.description,'gross':str(i.gross_amount),'discount':str(i.discount_amount),'amount':str(i.amount)} for i in row.service_lines.all()])
    if isinstance(row,Customer):
        data['name']=row.full_name;data.pop('outstanding_balance',None)
    if isinstance(row,SchoolInvoiceLink):
        invoice=row.invoice;data.update(name=invoice.invoice_number,number=invoice.invoice_number,student_name=str(row.enrollment.student),customer_name=invoice.customer.full_name,customer_id=str(invoice.customer_id),total_amount=str(invoice.total_amount),amount_paid=str(invoice.amount_paid),balance=str(balance(invoice)),status=invoice.status,due_date=str(invoice.due_date))
    if isinstance(row,FeeBatch):data['name']=f'{row.structure.name} · {row.issue_date} · {row.status}'
    if isinstance(row,FeeStructureLine):data['name']=str(row)
    if isinstance(row,ServiceInvoiceLine):data.update(name=f'{row.invoice.invoice_number} · {row.description}',invoice_number=row.invoice.invoice_number)
    if isinstance(row,BillingReceipt):data.update(name=str(row),customer_name=row.customer.full_name,method_name=row.method.name,available=str(available(row)))
    if isinstance(row,(BillingAllocation,BillingCredit)):data.update(invoice_number=row.invoice.invoice_number,name=f'{row._meta.verbose_name.title()} · {row.invoice.invoice_number}')
    if isinstance(row,(FeeDiscount,StudentFeeAssignment)):data.update(student_name=str(row.enrollment.student),fee_name=str(row.line))
