"""Fee master validation and explicit discount approval."""
from django.db import transaction
from django.utils import timezone
from apps.school.models.fees import *
from apps.school.models import AcademicYear,AcademicTerm,SchoolClass,StudentEnrollment
from apps.school.fee_contracts import MODELS,RESOURCES,READ_ONLY
from apps.school.serializers.sis import validate_input
from apps.sales.models.billing import BillingMethod
from apps.customers.models import Customer
from apps.finance.models import CostCenter,BusinessUnit
from apps.sales.services import billing_service as billing
from .sis_common import get,invalid,persist,lock,reason


def finance_settings(access,branch):
    access.campus(branch.pk)
    row=SchoolFinanceSettings.objects.filter(tenant=access.tenant,branch=branch,deleted_at__isnull=True).first()
    if not row:invalid('settings','Configure School finance mappings before billing.')
    for dimension in ('cost_center','business_unit'):
        item=getattr(row,dimension)
        if item and (item.tenant_id!=access.tenant.pk or item.deleted_at or not item.is_active):invalid(dimension,'Choose an active tenant dimension.')
    return row

def enrollment_for(enrollment,structure):
    if enrollment.branch_id!=structure.branch_id or enrollment.academic_year_id!=structure.academic_year_id or enrollment.school_class_id!=structure.school_class_id or enrollment.status!='active' or enrollment.student.status!='active' or enrollment.student.deleted_at or enrollment.student.branch_id!=structure.branch_id:invalid('enrollment_id','Choose an active student enrollment in this structure year/class/campus.')

class FeeCrud:
    @staticmethod
    @transaction.atomic
    def save(resource,data,*,access,pk=None):
        access.require(RESOURCES[resource],'update' if pk else 'create');billing.require(access,write=False);lock(access)
        if resource in READ_ONLY:invalid('action','Use the authorized financial workflow.')
        if not access.user.has_permission('finance.create'):billing.fail('finance.create permission is required.')
        row=get(access,MODELS[resource],pk) if pk else MODELS[resource](tenant=access.tenant)
        values=validate_input(resource,data,partial=bool(pk))
        for key,value in values.items():
            if pk and key.endswith('_id') and str(value)!=str(getattr(row,key)):invalid(key,'Relationships are immutable.')
            setattr(row,key,value)
        if isinstance(row,(SchoolFinanceSettings,FeeCategory,FeeStructure,BillingMethod,Customer)):row.branch=access.campus(row.branch_id)
        if isinstance(row,Customer) and not access.user.has_permission('customers.update' if pk else 'customers.create'):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Shared customer write permission is required.')
        if isinstance(row,SchoolFinanceSettings):
            billing.account(access,row.receivable_mapping_key,('asset',));billing.account(access,row.advance_mapping_key,('liability',));billing.account(access,row.credit_mapping_key,('expense','revenue'))
            for key,model in [('cost_center',CostCenter),('business_unit',BusinessUnit)]:
                if getattr(row,key+'_id'):
                    item=get(access,model,getattr(row,key+'_id'))
                    if not item.is_active:invalid(key,'Dimension is inactive.')
                    setattr(row,key,item)
        elif isinstance(row,BillingMethod):billing.account(access,row.account_mapping_key,('asset',))
        elif isinstance(row,FeeCategory):
            billing.account(access,row.revenue_mapping_key,('liability',) if row.recognition=='deferred' else ('revenue',))
            if pk and FeeStructureLine.objects.filter(category=row,structure__status='active').exists():invalid('category','Close linked active structures before editing their fee category.')
        elif isinstance(row,FeeStructure):
            if row.status!='draft':invalid('status','Only draft structures can be edited.')
            row.academic_year=get(access,AcademicYear,row.academic_year_id);row.school_class=get(access,SchoolClass,row.school_class_id)
            if row.academic_year.branch_id!=row.branch_id or row.school_class.branch_id!=row.branch_id or row.school_class.status!='active':invalid('school_class_id','Calendar/class must belong to this campus and class must be active.')
            if row.term_id:
                row.term=get(access,AcademicTerm,row.term_id)
                if row.term.academic_year_id!=row.academic_year_id:invalid('term_id','Term must belong to the year.')
        elif isinstance(row,FeeStructureLine):
            row.structure=get(access,FeeStructure,row.structure_id);row.category=get(access,FeeCategory,row.category_id);row.branch=row.structure.branch
            if row.structure.status!='draft':invalid('structure_id','Only draft fee structures accept changes.')
            if row.category.branch_id!=row.branch_id or row.category.status!='active':invalid('category_id','Choose an active category in this campus.')
            year=row.structure.academic_year
            if not year.start_date<=row.due_date<=year.end_date:invalid('due_date','Due date must fall within the academic year.')
            if not row.period_key.strip():invalid('period_key','A stable charge period key is required.')
        elif isinstance(row,FeeDiscount):
            if row.status!='requested':invalid('status','Decided discounts are immutable.')
            row.enrollment=get(access,StudentEnrollment,row.enrollment_id);row.line=get(access,FeeStructureLine,row.line_id);row.branch=row.line.branch
            enrollment_for(row.enrollment,row.line.structure)
            if row.value>(100 if row.kind=='percentage' else row.line.amount):invalid('value','Discount exceeds the fee.')
            if StudentFeeAssignment.objects.filter(enrollment=row.enrollment,line=row.line).exists():invalid('line_id','Use a credit for an issued charge.')
        return persist(row,access,'fee_updated' if pk else 'fee_created')

    @staticmethod
    @transaction.atomic
    def action(resource,pk,action,data,*,access):
        access.require(RESOURCES[resource],action);billing.require(access,approve=True);lock(access);row=get(access,MODELS[resource],pk)
        if resource=='fee-structures':
            if action=='activate' and row.status=='draft' and row.lines.filter(deleted_at__isnull=True).exists():row.status='active'
            elif action=='close' and row.status=='active':row.status='closed'
            else:invalid('status','Use draft → activate → close; active structures need lines.')
        elif resource=='fee-discounts':
            if row.status!='requested' or action not in ('approve','reject'):invalid('status','Discount decision already recorded.')
            if StudentFeeAssignment.objects.filter(enrollment=row.enrollment,line=row.line).exists():invalid('line_id','Charge already issued; use a credit.')
            row.status='approved' if action=='approve' else 'rejected';row.approved_by=access.user
        else:invalid('action','Unknown fee command.')
        return persist(row,access,'fee_'+action)
