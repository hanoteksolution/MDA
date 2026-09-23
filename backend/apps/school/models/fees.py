"""School fee expectations and links to the shared billing/ledger foundation."""
from django.db import models
from django.db.models import Q
from .sis_identity import SchoolRecord,ref,choices

def money(**kwargs):return models.DecimalField(max_digits=18,decimal_places=2,**kwargs)

class SchoolFinanceSettings(SchoolRecord):
    receivable_mapping_key=models.CharField(max_length=50,default='SCHOOL_ACCOUNTS_RECEIVABLE')
    advance_mapping_key=models.CharField(max_length=50,default='SCHOOL_ADVANCES')
    credit_mapping_key=models.CharField(max_length=50,default='SCHOOL_SCHOLARSHIP_DISCOUNT')
    cost_center=ref('finance.CostCenter',optional=True)
    business_unit=ref('finance.BusinessUnit',optional=True)
    class Meta:constraints=[models.UniqueConstraint(fields=['tenant','branch'],name='school_finance_settings')]

class FeeCategory(SchoolRecord):
    name=models.CharField(max_length=100)
    code=models.CharField(max_length=40)
    revenue_mapping_key=models.CharField(max_length=50)
    recognition=models.CharField(max_length=20,choices=choices('revenue deferred'),default='revenue')
    status=models.CharField(max_length=20,choices=choices('active inactive'),default='active')
    class Meta:constraints=[models.UniqueConstraint(fields=['tenant','branch','code'],name='school_fee_category_code')]
    def __str__(self):return self.name

class FeeStructure(SchoolRecord):
    name=models.CharField(max_length=120)
    academic_year=ref('school.AcademicYear')
    school_class=ref('school.SchoolClass')
    term=ref('school.AcademicTerm',optional=True)
    status=models.CharField(max_length=20,choices=choices('draft active closed'),default='draft')
    def __str__(self):return self.name

class FeeStructureLine(SchoolRecord):
    structure=ref(FeeStructure,related_name='lines')
    category=ref(FeeCategory)
    period_key=models.CharField(max_length=50)
    amount=money()
    due_date=models.DateField()
    class Meta:constraints=[models.UniqueConstraint(fields=['structure','category','period_key'],name='school_fee_line_period'),models.CheckConstraint(condition=Q(amount__gt=0),name='school_fee_positive')]
    def __str__(self):return f'{self.category}: {self.period_key}'

class FeeDiscount(SchoolRecord):
    enrollment=ref('school.StudentEnrollment')
    line=ref(FeeStructureLine)
    kind=models.CharField(max_length=20,choices=choices('percentage amount'))
    value=money()
    reason=models.TextField()
    status=models.CharField(max_length=20,choices=choices('requested approved rejected'),default='requested')
    approved_by=ref('authentication.User',optional=True)
    class Meta:constraints=[models.UniqueConstraint(fields=['enrollment','line'],name='school_fee_discount_one'),models.CheckConstraint(condition=Q(value__gt=0),name='school_discount_positive')]

class FeeBatch(SchoolRecord):
    structure=ref(FeeStructure)
    issue_date=models.DateField()
    snapshot=models.JSONField()
    fingerprint=models.CharField(max_length=64)
    status=models.CharField(max_length=20,default='preview')

class SchoolInvoiceLink(SchoolRecord):
    invoice=ref('sales.Invoice',one=True)
    enrollment=ref('school.StudentEnrollment')
    family=ref('school.Family',optional=True)
    batch=ref(FeeBatch)
    class Meta:constraints=[models.UniqueConstraint(fields=['batch','enrollment'],name='school_batch_invoice')]

class StudentFeeAssignment(SchoolRecord):
    enrollment=ref('school.StudentEnrollment')
    category=ref(FeeCategory)
    period_key=models.CharField(max_length=50)
    line=ref(FeeStructureLine)
    invoice_line=ref('sales.ServiceInvoiceLine',one=True)
    gross_amount=money()
    discount_amount=money(default=0)
    amount=money()
    class Meta:constraints=[models.UniqueConstraint(fields=['enrollment','category','period_key'],name='school_charge_period_unique')]
