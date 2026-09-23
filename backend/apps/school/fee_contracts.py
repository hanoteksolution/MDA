"""Phase 6 SIS resource contracts; financial actions are dedicated commands."""
from apps.school.models.fees import *
from apps.sales.models.billing import BillingMethod,BillingReceipt,BillingAllocation,BillingCredit,BillingRefund,ServiceInvoiceLine
from apps.customers.models import Customer
from apps.sales.models import Invoice
from apps.finance.models import CostCenter,BusinessUnit
MODELS={'billing-invoices':Invoice,'fee-settings':SchoolFinanceSettings,'fee-categories':FeeCategory,'fee-structures':FeeStructure,'fee-lines':FeeStructureLine,'fee-discounts':FeeDiscount,'fee-batches':FeeBatch,'fee-assignments':StudentFeeAssignment,'fee-invoices':SchoolInvoiceLink,'billing-methods':BillingMethod,'billing-customers':Customer,'billing-receipts':BillingReceipt,'billing-allocations':BillingAllocation,'billing-credits':BillingCredit,'billing-refunds':BillingRefund,'billing-lines':ServiceInvoiceLine,'billing-cost-centers':CostCenter,'billing-business-units':BusinessUnit}
RESOURCES={key:('fee_invoice' if key in ('billing-lines','billing-invoices') else 'fee_settings' if key in ('fee-settings','billing-cost-centers','billing-business-units') else key.replace('-','_').rstrip('s')) for key in MODELS}
RESOURCES.update({'fee-categories':'fee_category','fee-batches':'fee_batch'})
FIELDS={'fee-settings':'branch_id receivable_mapping_key advance_mapping_key credit_mapping_key cost_center_id business_unit_id','fee-categories':'branch_id name code revenue_mapping_key recognition status','fee-structures':'branch_id name academic_year_id school_class_id term_id','fee-lines':'structure_id category_id period_key amount due_date','fee-discounts':'enrollment_id line_id kind value reason','billing-methods':'branch_id code name account_mapping_key is_active','billing-customers':'branch_id customer_code full_name phone email address'}
READ_ONLY=set(MODELS)-set(FIELDS)
FIELDS.update({key:'' for key in READ_ONLY})
# Read aliases share one canonical permission and label in the global catalog.
PERMISSIONS=list({f'school.{RESOURCES[k]}.{a}':(f'school.{RESOURCES[k]}.{a}',f'School {RESOURCES[k]}: {a}','school') for k in MODELS for a in (('view',) if k in READ_ONLY else ('view','create','update'))}.values())
PERMISSIONS += [(f'school.{r}.{a}',f'School {r}: {a}','school') for r,actions in {'fee_structure':('activate','close'),'fee_discount':('approve','reject'),'fee_batch':('preview','issue'),'billing_receipt':('collect','reverse'),'billing_allocation':('allocate','reverse'),'billing_credit':('issue','reverse'),'billing_refund':('issue','reverse'),'fee_finance':('view',)}.items() for a in actions]
