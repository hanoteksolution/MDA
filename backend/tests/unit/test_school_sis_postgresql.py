"""Phase 3 concurrent HTTP commands on real PostgreSQL."""
import pytest
from apps.school.models import Student, StudentEnrollment, SchoolAdmissionPolicy
from apps.school.repositories.sis import StudentAccess
from apps.school.services.sis_crud import StudentCrudService as Crud
from apps.school.services import admission_workflow as admissions
from apps.school.services.foundation_service import FoundationService as Service
from tests.unit.test_school_postgresql import setup_school, race

pytestmark = pytest.mark.django_db(transaction=True)

@pytest.fixture
def ready(setup_school):
    s=setup_school
    Service.save('academic-years',{'admission_open':True,'enrollment_open':True},pk=s['year'].pk,user=s['owner'])
    Service.action('academic-years',s['year'].pk,'activate',user=s['owner'])
    s['klass'].capacity=1;s['klass'].save()
    SchoolAdmissionPolicy.objects.create(tenant=s['tenant'],branch=s['branch'],require_guardian=False)
    s['access']=StudentAccess(user=s['owner'])
    return s


def test_concurrent_conversion_returns_one_student(ready):
    s=ready
    applicant=Crud.save('applicants',{'branch_id':str(s['branch'].pk),'first_name':'Amina','date_of_birth':'2015-02-02'},access=s['access'])
    app=Crud.save('applications',{'branch_id':str(s['branch'].pk),'applicant_id':str(applicant.pk),'academic_year_id':str(s['year'].pk),'school_class_id':str(s['klass'].pk)},access=s['access'])
    for action in ('submit','review','under-review'):admissions.transition(app.pk,action,{},access=s['access'])
    admissions.decide(app.pk,{'decision':'accepted','reason':'Approved'},access=s['access'])
    request=(f'/api/v1/school/sis/applications/{app.pk}/enroll/',{'placement':{'start_date':'2026-09-01'}})
    results=race(s['owner'],[request,request])
    assert [code for code,_ in results]==[200,200],results
    assert results[0][1]['data']['id']==results[1][1]['data']['id']
    assert Student.objects.count()==1 and StudentEnrollment.objects.count()==1


def test_concurrent_capacity_does_not_overbook(ready):
    s=ready
    placement={'branch_id':str(s['branch'].pk),'academic_year_id':str(s['year'].pk),'school_class_id':str(s['klass'].pk),'start_date':'2026-09-01'}
    requests=[('/api/v1/school/sis/students/',{'student':{'branch_id':str(s['branch'].pk),'first_name':name,'date_of_birth':'2015-02-02'},'placement':placement,'reason':'Registration'}) for name in ('One','Two')]
    results=race(s['owner'],requests)
    assert sorted(code for code,_ in results)==[201,400],results
    assert Student.objects.count()==1 and StudentEnrollment.objects.filter(status='active').count()==1
