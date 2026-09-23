"""Fee preview/issue with stable charge-period identity and accounting rollback."""
from decimal import Decimal,ROUND_HALF_UP
from django.db import transaction
from apps.school.models.fees import *
from apps.school.models import StudentEnrollment
from apps.customers.models import Customer
from apps.sales.services import billing_service as billing
from .sis_common import get,lock,persist,invalid
from .fee_crud import finance_settings,enrollment_for


def build(data,access):
    structure=get(access,FeeStructure,data.get('structure_id'))
    if structure.status!='active':invalid('structure_id','Activate this structure before generating fees.')
    settings=finance_settings(access,structure.branch);day=billing.date(data,'issue_date')
    if not structure.academic_year.start_date<=day<=structure.academic_year.end_date:invalid('issue_date','Issue date must fall within the academic year.')
    lines=list(structure.lines.filter(deleted_at__isnull=True).select_related('category').order_by('pk'))
    if not lines:invalid('lines','Fee structure is empty.')
    values=data.get('students')
    if not isinstance(values,list) or not 1<=len(values)<=200:invalid('students','Choose 1–200 enrolled students.')
    ar=billing.account(access,settings.receivable_mapping_key,('asset',));advance=billing.account(access,settings.advance_mapping_key,('liability',));credit=billing.account(access,settings.credit_mapping_key,('expense','revenue'))
    snapshot={'structure_id':str(structure.pk),'issue_date':str(day),'structure_updated':str(structure.updated_at),'settings_updated':str(settings.updated_at),'accounts':[(str(a.pk),str(a.updated_at)) for a in (ar,advance,credit)],'students':[]};seen=set();prepared=[]
    for value in values:
        if not isinstance(value,dict) or set(value)-{'enrollment_id','customer_id'}:invalid('students','Choose enrollment and billing customer for each student.')
        enrollment=get(access,StudentEnrollment,value.get('enrollment_id'));customer=get(access,Customer,value.get('customer_id'));enrollment_for(enrollment,structure)
        if enrollment.pk in seen:invalid('students','A student appears more than once.')
        seen.add(enrollment.pk)
        if enrollment.start_date>day or (enrollment.end_date and enrollment.end_date<day):invalid('enrollment_id','Student is not enrolled on the issue date.')
        if customer.branch_id!=structure.branch_id or not customer.is_active:invalid('customer_id','Choose an active customer in this campus.')
        person={'enrollment_id':str(enrollment.pk),'customer_id':str(customer.pk),'name':str(enrollment.student),'customer':customer.full_name,'enrollment_updated':str(enrollment.updated_at),'student_updated':str(enrollment.student.updated_at),'customer_updated':str(customer.updated_at),'lines':[]};rows=[]
        for item in lines:
            if item.category.status!='active':invalid('category','A category has been deactivated.')
            if StudentFeeAssignment.objects.filter(enrollment=enrollment,category=item.category,period_key=item.period_key).exists():invalid('period_key','A charge for this enrollment/category/period is already issued.')
            discount=FeeDiscount.objects.filter(enrollment=enrollment,line=item,status='approved',deleted_at__isnull=True).first()
            reduction=(item.amount*discount.value/100 if discount.kind=='percentage' else discount.value).quantize(Decimal('.01'),rounding=ROUND_HALF_UP) if discount else Decimal('0.00')
            if reduction>item.amount:invalid('discount','Discount exceeds this fee.')
            revenue=billing.account(access,item.category.revenue_mapping_key,('liability',) if item.category.recognition=='deferred' else ('revenue',))
            person['lines'].append({'line_id':str(item.pk),'description':f'{item.category.name} · {item.period_key}','gross':str(item.amount),'discount':str(reduction),'net':str(item.amount-reduction),'due_date':str(item.due_date),'line_updated':str(item.updated_at),'category_updated':str(item.category.updated_at),'discount_updated':str(discount.updated_at) if discount else None,'revenue_account_id':str(revenue.pk),'account_updated':str(revenue.updated_at)})
            rows.append({'description':person['lines'][-1]['description'],'gross':item.amount,'discount':reduction,'revenue':revenue,'fee_line':item})
        person['total']=str(sum((r['gross']-r['discount'] for r in rows),Decimal('0.00')));snapshot['students'].append(person);prepared.append((enrollment,customer,rows))
    return structure,settings,day,snapshot,prepared

@transaction.atomic
def preview(data,*,access):
    access.require('fee_batch','preview');billing.require(access);lock(access)
    structure,settings,day,snapshot,_=build(data,access)
    row=FeeBatch(tenant=access.tenant,branch=structure.branch,structure=structure,issue_date=day,snapshot=snapshot,fingerprint=billing.digest(snapshot))
    return persist(row,access,'fee_previewed')

@transaction.atomic
def issue(pk,data,*,access):
    access.require('fee_batch','issue');billing.require(access,approve=True);lock(access);batch=get(access,FeeBatch,pk)
    if data.get('fingerprint')!=batch.fingerprint:invalid('fingerprint','Confirm the saved preview before issuing fees.')
    if batch.status=='issued':return batch
    request={'structure_id':str(batch.structure_id),'issue_date':str(batch.issue_date),'students':[{k:r[k] for k in ('enrollment_id','customer_id')} for r in batch.snapshot['students']]}
    structure,settings,day,snapshot,prepared=build(request,access)
    if billing.digest(snapshot)!=batch.fingerprint:invalid('preview','Fees, mappings, discounts or enrollment changed. Generate a fresh preview.')
    for enrollment,customer,rows in prepared:
        inv=billing.issue_service_invoice(access=access,branch=batch.branch,customer=customer,on_date=day,due_date=min(r['fee_line'].due_date for r in rows),rows=rows,settings=settings,idempotency_key=billing.digest([str(batch.pk),str(enrollment.pk)]))
        persist(SchoolInvoiceLink(tenant=access.tenant,branch=batch.branch,invoice=inv,enrollment=enrollment,family=enrollment.student.family,batch=batch),access,'school_invoice_issued')
        items=list(inv.service_lines.order_by('created_at','pk'))
        for r,item in zip(rows,items):
            source=r['fee_line'];persist(StudentFeeAssignment(tenant=access.tenant,branch=batch.branch,enrollment=enrollment,category=source.category,period_key=source.period_key,line=source,invoice_line=item,gross_amount=r['gross'],discount_amount=r['discount'],amount=r['gross']-r['discount']),access,'fee_assigned')
    batch.status='issued';return persist(batch,access,'fee_batch_issued')
