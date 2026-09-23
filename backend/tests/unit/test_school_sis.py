"""SIS lifecycle tests use real services and HTTP authorization boundaries."""
import pytest
from rest_framework.exceptions import ValidationError, NotFound
from apps.school.models import Student, SchoolAdmissionPolicy
from apps.school.repositories.sis import StudentAccess
from apps.school.services.sis_crud import StudentCrudService as Crud
from apps.school.services import admission_workflow as admissions, student_creation, student_lifecycle
from tests.unit.test_school_foundation import school_catalog, school, structure, year, Service

pytestmark=pytest.mark.django_db

@pytest.fixture
def sis(school):
    s=school;k,_,sec=structure(s);y=year(s)
    Service.save('academic-years', {'enrollment_open': True, 'admission_open': True}, pk=y.pk, user=s['owner'])
    Service.action('academic-years',y.pk,'activate',user=s['owner'])
    access=StudentAccess(user=s['owner'])
    SchoolAdmissionPolicy.objects.create(tenant=s['t'],branch=s['a'],require_guardian=False)
    s.update(k=k,sec=sec,y=y,access=access)
    s['placement']={'branch_id':str(s['a'].pk),'academic_year_id':str(y.pk),'school_class_id':str(k.pk),'section_id':str(sec.pk),'start_date':'2026-09-01'}
    s['client'].force_authenticate(s['owner'])
    return s


def direct(s,**extra):
    return student_creation.direct({'student':{'branch_id':str(s['a'].pk),'first_name':'Amina','last_name':'Hassan','date_of_birth':'2015-02-02',**extra},'placement':s['placement'],'reason':'Legacy registration'},access=s['access'])


def application(s):
    applicant=Crud.save('applicants',{'branch_id':str(s['a'].pk),'first_name':'Ali','last_name':'Hassan','date_of_birth':'2016-03-02'},access=s['access'])
    app=Crud.save('applications',{'branch_id':str(s['a'].pk),'applicant_id':str(applicant.pk),'academic_year_id':str(s['y'].pk),'school_class_id':str(s['k'].pk),'section_id':str(s['sec'].pk)},access=s['access'])
    for action in ('submit','review','under-review'):admissions.transition(app.pk,action,{},access=s['access'])
    return app


def test_direct_and_current(sis):
    from apps.school.repositories.sis import queryset
    s=sis;student=direct(s)
    row=queryset('students',s['access']).get(pk=student.pk)
    assert row.current_class==s['k'].name and row.current_enrollment_id
    assert row.number.startswith('STU-2026-')
    for path in ('students/','students/'+str(row.pk)+'/','dashboard/','capabilities/','students/schema/','students/'+str(row.pk)+'/activity/'):
        response=s['client'].get('/api/v1/school/sis/'+path)
        assert response.status_code==200,response.data


def test_conversion_atomic_and_duplicate(sis):
    s=sis;app=application(s)
    admissions.decide(app.pk,{'decision':'accepted','reason':'Approved'},access=s['access'])
    with pytest.raises(ValidationError):student_creation.convert(app.pk,{'placement':{'start_date':'2030-01-01'}},access=s['access'])
    assert not Student.objects.exists()
    student=student_creation.convert(app.pk,{'placement':{'start_date':'2026-09-01'}},access=s['access'])
    assert student.enrollments.count()==1
    assert student_creation.convert(app.pk,{'placement':{'start_date':'2026-09-01'}},access=s['access']).pk == student.pk
    assert Student.objects.count()==1


def test_guardian_required_roll_capacity(sis):
    s=sis;config=SchoolAdmissionPolicy.objects.get(tenant=s['t']);config.require_guardian=True;config.save()
    with pytest.raises(ValidationError):direct(s)
    assert not Student.objects.exists()
    config.require_guardian=False;config.save()
    s['placement']['roll_number']='01';direct(s)
    with pytest.raises(ValidationError):direct(s,first_name='Other')
    assert Student.objects.count()==1


def test_transfer_withdraw_reenroll(sis):
    s=sis;student=direct(s);source=student.enrollments.get()
    data={'enrollment_id':str(source.pk),'effective_date':'2026-09-02','reason':'Placement review','placement':{**s['placement'],'section_id':None}}
    student_lifecycle.transition(student.pk,'transfer',data,access=s['access'])
    with pytest.raises(ValidationError):student_lifecycle.transition(student.pk,'transfer',data,access=s['access'])
    source.refresh_from_db();assert source.status=='transferred' and source.end_date.isoformat()=='2026-09-01'
    active=student.enrollments.get(status='active')
    student_lifecycle.transition(student.pk,'withdraw',{'enrollment_id':str(active.pk),'effective_date':'2026-09-03','reason':'Relocation'},access=s['access'])
    student_lifecycle.transition(student.pk,'reenroll',{'effective_date':'2026-09-04','reason':'Returned','placement':s['placement']},access=s['access'])
    assert student.enrollments.count()==3 and student.enrollments.filter(status='active').count()==1


def test_scope_and_status_patch(sis):
    s=sis;student=direct(s)
    response=s['client'].patch(f'/api/v1/school/sis/students/{student.pk}/',{'status':'graduated'},format='json')
    assert response.status_code==400
    with pytest.raises(NotFound):student_creation.direct({'student':{'branch_id':str(s['b'].pk),'first_name':'X','last_name':'Y','date_of_birth':'2015-01-01'},'placement':s['placement'],'reason':'Test'},access=StudentAccess(user=s['u']))
    assert Student.objects.count()==1


def test_admission_calendar_and_close_guards(sis):
    s=sis;student=direct(s)
    with pytest.raises(ValidationError):Service.action('academic-years',s['y'].pk,'close',user=s['owner'])
    with pytest.raises(ValidationError):Service.save('academic-years',{'start_date':'2026-09-02'},pk=s['y'].pk,user=s['owner'])
    Service.save('academic-years',{'enrollment_open':False},pk=s['y'].pk,user=s['owner'])
    with pytest.raises(ValidationError):direct(s,first_name='Blocked')
    assert Student.objects.count()==1
    assert student.enrollments.get().status=='active'


def test_family_guardian_reuse_and_conversion(sis):
    s=sis
    guardian=Crud.save('guardians',{'branch_id':str(s['a'].pk),'first_name':'Parent','phone':'1234'},access=s['access'])
    family=Crud.save('families',{'branch_id':str(s['a'].pk),'code':'HOME','name':'Household','primary_guardian_id':str(guardian.pk)},access=s['access'])
    relation=Crud.save('relationship-types',{'name':'Parent','code':'PARENT'},access=s['access'])
    app=application(s)
    Crud.save('applicants',{'family_id':str(family.pk)},pk=app.applicant_id,access=s['access'])
    Crud.save('applicant-guardians',{'applicant_id':str(app.applicant_id),'guardian_id':str(guardian.pk),'relationship_id':str(relation.pk),'start_date':'2026-09-01','is_primary':True},access=s['access'])
    config=SchoolAdmissionPolicy.objects.get(tenant=s['t']);config.require_guardian=True;config.require_family=True;config.save()
    admissions.decide(app.pk,{'decision':'accepted','reason':'Approved'},access=s['access'])
    student=student_creation.convert(app.pk,{'placement':{'start_date':'2026-09-01'}},access=s['access'])
    assert student.family_id==family.pk
    assert student.guardian_links.get().guardian_id==guardian.pk
    assert student_creation.convert(app.pk,{},access=s['access']).pk==student.pk
    assert guardian.studentguardian_records.count()==1


def test_cross_campus_transfer_preserves_private_identity_and_history(sis,settings,tmp_path):
    from apps.school.repositories.sis import queryset
    import io
    from PIL import Image
    from django.core.files.uploadedfile import SimpleUploadedFile
    from apps.school.services import private_files
    from apps.authentication.models import User,Role
    s=sis;settings.SCHOOL_PRIVATE_ROOT=str(tmp_path)
    image=io.BytesIO();Image.new('RGB',(2,2)).save(image,format='PNG')
    photo=private_files.upload(SimpleUploadedFile('photo.png',image.getvalue()),s['a'].pk,access=s['access'],purpose='student_photo')
    student=direct(s,photo_id=str(photo.pk));source=student.enrollments.get()
    target_class=Service.save('classes',{'branch_id':str(s['b'].pk),'education_level_id':str(s['k'].education_level_id),'code':'B5','name':'B Grade','capacity':30},user=s['owner'])
    target_year=year(s,'b','B-YEAR')
    Service.save('academic-years',{'enrollment_open':True},pk=target_year.pk,user=s['owner'])
    Service.action('academic-years',target_year.pk,'activate',user=s['owner'])
    SchoolAdmissionPolicy.objects.create(tenant=s['t'],branch=s['b'],require_guardian=False)
    data={'enrollment_id':str(source.pk),'effective_date':'2026-09-02','reason':'Move campus','placement':{'branch_id':str(s['b'].pk),'academic_year_id':str(target_year.pk),'school_class_id':str(target_class.pk)}}
    with pytest.raises(NotFound):student_lifecycle.transition(student.pk,'transfer',data,access=StudentAccess(user=s['u']))
    source.refresh_from_db();assert source.status=='active'
    student_lifecycle.transition(student.pk,'transfer',data,access=s['access'])
    student.refresh_from_db();source.refresh_from_db()
    assert student.branch_id==s['b'].pk and source.branch_id==s['a'].pk and source.status=='transferred'
    target_principal=User.objects.create_user(username='target-principal',tenant=s['t'],branch=s['b'],role=Role.objects.get(slug='school_principal'))
    target_access=StudentAccess(user=target_principal)
    assert private_files.download(photo.pk,access=target_access)[0].pk==photo.pk
    Crud.save('students',{'preferred_name':'Transferred'},pk=student.pk,access=target_access)
    with pytest.raises(NotFound):private_files.download(photo.pk,access=StudentAccess(user=s['u']))
    old_access=StudentAccess(user=s['u'])
    assert not queryset('students',old_access).filter(pk=student.pk).exists()
    assert queryset('enrollments',old_access).filter(pk=source.pk).exists()
    s['client'].force_authenticate(s['u'])
    assert s['client'].get(f'/api/v1/school/sis/students/{student.pk}/').status_code==404


def test_audit_failure_rolls_back_student_number_and_enrollment(sis,monkeypatch):
    from apps.school.models import SchoolSequence
    s=sis
    def fail(**kwargs):raise RuntimeError('Audit unavailable')
    monkeypatch.setattr('apps.school.services.sis_common.write_audit',fail)
    with pytest.raises(RuntimeError):direct(s)
    assert not Student.objects.exists() and not SchoolSequence.objects.filter(kind='student').exists()


def test_security_denies_foreign_read_writes_and_confidential_notes(sis):
    s=sis;student=direct(s)
    note=Crud.save('notes',{'student_id':str(student.pk),'title':'Restricted','body':'Private text','category':'confidential'},access=s['access'])
    s['client'].force_authenticate(s['u'])
    assert s['client'].get(f'/api/v1/school/sis/notes/{note.pk}/').status_code==404
    assert s['client'].get('/api/v1/school/sis/notes/').data['data']['count']==0
    from apps.audit.models import AuditLog
    assert 'Private text' not in str(list(AuditLog.objects.filter(entity_id=note.pk).values('new_values','old_values')))
    s['client'].force_authenticate(s['foreign'])
    assert s['client'].get(f'/api/v1/school/sis/students/{student.pk}/').status_code in (403,404)
    assert s['client'].patch(f'/api/v1/school/sis/students/{student.pk}/',{'first_name':'No'},format='json').status_code in (403,404)


def test_capacity_and_roll_conflicts_are_atomic(sis):
    s=sis;s['k'].capacity=1;s['k'].save();s['sec'].capacity=1;s['sec'].save()
    direct(s)
    with pytest.raises(ValidationError):direct(s,first_name='Second')
    assert Student.objects.count()==1


def test_required_document_and_private_download(sis,settings,tmp_path):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from apps.school.services import private_files,document_service
    s=sis;settings.SCHOOL_PRIVATE_ROOT=str(tmp_path);app=application(s)
    kind=Crud.save('document-types',{'branch_id':str(s['a'].pk),'name':'Birth certificate','code':'BIRTH','required':True},access=s['access'])
    with pytest.raises(ValidationError):admissions.decide(app.pk,{'decision':'accepted','reason':'Approve'},access=s['access'])
    file=private_files.upload(SimpleUploadedFile('birth.pdf',b'%PDF-1.4\n%%EOF'),s['a'].pk,access=s['access'],purpose='admission')
    doc=Crud.save('applicant-documents',{'application_id':str(app.pk),'document_type_id':str(kind.pk),'file_id':str(file.pk)},access=s['access'])
    document_service.verify('applicant-documents',doc.pk,{'verification_status':'verified'},access=s['access'])
    admissions.decide(app.pk,{'decision':'accepted','reason':'Approve'},access=s['access'])
    student=student_creation.convert(app.pk,{'placement':{'start_date':'2026-09-01'}},access=s['access'])
    assert student.documents.get().file_id==file.pk
    response=s['client'].get(f'/api/v1/school/sis/files/{file.pk}/')
    assert response.status_code==200 and response['Cache-Control']=='private, no-store'
    from apps.platform.services.module_service import sync_tenant_modules
    sync_tenant_modules(tenant=s['foreign'].tenant,enabled_codes=['school','sales','inventory'])
    with pytest.raises(NotFound):private_files.download(file.pk,access=StudentAccess(user=s['foreign']))
    response.close()


@pytest.mark.parametrize('body',[{'student':[]},{'student':{},'placement':[]},{'student':{},'guardians':['bad']}])
def test_malformed_nested_student_payload_is_controlled(sis,body):
    response=sis['client'].post('/api/v1/school/sis/students/',{'reason':'Registration',**body},format='json')
    assert response.status_code==400,response.data
    assert not Student.objects.exists()


def test_teacher_cannot_create_or_advance_admissions(sis):
    from apps.authentication.models import Role,User
    s=sis;student=direct(s)
    teacher=User.objects.create_user(username='sis-teacher',tenant=s['t'],branch=s['a'],role=Role.objects.get(slug='school_teacher'))
    s['client'].force_authenticate(teacher)
    assert s['client'].get(f'/api/v1/school/sis/students/{student.pk}/').status_code==200
    assert s['client'].post('/api/v1/school/sis/students/',{},format='json').status_code==403
    assert s['client'].post(f'/api/v1/school/sis/students/{student.pk}/withdraw/',{'reason':'No','effective_date':'2026-09-02'},format='json').status_code==403
    student.refresh_from_db();assert student.status=='active'


def test_export_is_scoped_and_formula_safe(sis):
    s=sis;direct(s,first_name='=HYPERLINK("bad")')
    response=s['client'].get('/api/v1/school/sis/students/export/')
    assert response.status_code==200
    assert "'=HYPERLINK" in response.content.decode()
    assert 'date_of_birth' not in response.content.decode()


def test_file_cannot_be_relinked_to_bypass_its_read_permission(sis,settings,tmp_path):
    import io
    from PIL import Image
    from django.core.files.uploadedfile import SimpleUploadedFile
    from apps.authentication.models import User,Role,Permission,UserPermission
    from apps.school.services import private_files
    s=sis;settings.SCHOOL_PRIVATE_ROOT=str(tmp_path);student=direct(s);app=application(s)
    image=io.BytesIO();Image.new('RGB',(2,2)).save(image,format='PNG')
    file=private_files.upload(SimpleUploadedFile('private.png',image.getvalue()),s['a'].pk,access=s['access'],purpose='admission')
    kind=Crud.save('document-types',{'name':'Private ID','code':'PRIVATE'},access=s['access'])
    Crud.save('applicant-documents',{'application_id':str(app.pk),'document_type_id':str(kind.pk),'file_id':str(file.pk)},access=s['access'])
    teacher=User.objects.create_user(username='photo-editor',tenant=s['t'],branch=s['a'],role=Role.objects.get(slug='school_teacher'))
    UserPermission.objects.create(user=teacher,permission=Permission.objects.get(codename='school.student.update'))
    access=StudentAccess(user=teacher)
    with pytest.raises(NotFound):Crud.save('students',{'photo_id':str(file.pk)},pk=student.pk,access=access)
    student.refresh_from_db();assert student.photo_id is None
