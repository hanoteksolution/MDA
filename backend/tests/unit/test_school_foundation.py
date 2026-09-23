import pytest
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError
from apps.authentication.models import User, Role
from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.platform.models import Tenant
from apps.platform.services.module_service import sync_tenant_modules
from apps.settings_app.models import Company, Branch
from apps.school.models import AcademicYear, SchoolCampusAccess
from apps.school.services.foundation_service import FoundationService as Service

pytestmark = pytest.mark.django_db

@pytest.fixture(scope="module")
def school_catalog(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        bootstrap_roles_and_permissions()

@pytest.fixture
def school(school_catalog):
    t=Tenant.objects.create(name='School',slug='school-test',currency='USD')
    other=Tenant.objects.create(name='Other',slug='school-other')
    sync_tenant_modules(tenant=t,enabled_codes=['school','sales','inventory'])
    c=Company.objects.create(tenant=t,name='School')
    a=Branch.objects.create(tenant=t,company=c,code='A',name='Campus A')
    b=Branch.objects.create(tenant=t,company=c,code='B',name='Campus B')
    u=User.objects.create_user(username='principal',tenant=t,branch=a,role=Role.objects.get(slug='school_principal'))
    owner=User.objects.create_user(username='owner',tenant=t,branch=a,role=Role.objects.get(slug='school_owner'))
    foreign=User.objects.create_user(username='foreign',tenant=other,role=Role.objects.get(slug='school_principal'))
    client=APIClient();client.force_authenticate(u)
    return dict(t=t,c=c,a=a,b=b,u=u,owner=owner,foreign=foreign,client=client)

def create(s,resource,**data):
    return Service.save(resource,data,user=s['owner'])

def year(s,branch='a',code='AY'):
    return create(s,'academic-years',name=code,code=code,branch_id=str(s[branch].pk),start_date='2026-09-01',end_date='2027-07-01')

def test_principal_validation(school):
    s=school
    for person in (s['foreign'],User.objects.create_user(username='pharmacist',tenant=s['t'],branch=s['a'])):
        r=s['client'].put('/api/v1/school/profile/',{'branch_id':str(s['a'].pk),'principal_user_id':str(person.pk)},format='json')
        assert r.status_code==400,r.data
    r=s['client'].put('/api/v1/school/profile/',{'branch_id':str(s['a'].pk),'principal_user_id':str(s['u'].pk)},format='json')
    assert r.status_code==200,r.data

def test_campus_idor_and_grant(school):
    s=school;y=year(s,'b');url=f'/api/v1/school/academic-years/{y.pk}/'
    assert s['client'].get(url).status_code==404
    assert s['client'].patch(url,{'name':'No'},format='json').status_code==404
    assert s['client'].get('/api/v1/school/academic-years/').data['data']['count']==0
    SchoolCampusAccess.objects.create(tenant=s['t'],user=s['u'],branch=s['b'])
    assert s['client'].get(url).status_code==200

def test_year_lifecycle_audit_and_constraint(school):
    s=school;a=year(s);b=year(s,code='AY2')
    Service.action('academic-years',a.pk,'activate',user=s['owner'])
    Service.action('academic-years',b.pk,'activate',user=s['owner'])
    a.refresh_from_db();b.refresh_from_db();assert not a.is_current and b.is_current
    with pytest.raises(IntegrityError),transaction.atomic(): AcademicYear.objects.filter(pk=a.pk).update(is_current=True,status='active')
    Service.action('academic-years',b.pk,'close',user=s['owner'])
    from apps.audit.models import AuditLog
    log=AuditLog.objects.get(entity_id=b.pk,action='close')
    assert log.old_values['status']=='active' and log.new_values['status']=='closed'
    Service.action('academic-years',b.pk,'archive',user=s['owner'])
    Service.action('academic-years',b.pk,'restore',user=s['owner'])
    b.refresh_from_db();assert b.status=='planning' and not b.deleted_at

@pytest.mark.parametrize('data',[{'start_date':'2027-09-01'},{'start_date':None},{'status':'active'},{'is_current':True}])
def test_invalid_year_edits(school,data):
    s=school;y=year(s)
    r=s['client'].patch(f'/api/v1/school/academic-years/{y.pk}/',data,format='json')
    assert r.status_code==400,r.data

def test_term_boundaries_overlap_and_close(school):
    s=school;y=year(s)
    t=create(s,'terms',name='First',code='T1',academic_year_id=str(y.pk),branch_id=str(s['a'].pk),start_date='2026-09-01',end_date='2026-12-01',sort_order=1)
    with pytest.raises(ValidationError): create(s,'terms',name='Second',code='T2',academic_year_id=str(y.pk),branch_id=str(s['a'].pk),start_date='2026-11-01',end_date='2027-02-01',sort_order=2)
    with pytest.raises(ValidationError): Service.action('academic-years',y.pk,'close',user=s['owner'])
    Service.action('terms',t.pk,'close',user=s['owner'])
    Service.action('academic-years',y.pk,'close',user=s['owner'])

def structure(s):
    level=create(s,'levels',name='Primary',code='PRI')
    klass=create(s,'classes',name='Grade 5',code='G5',branch_id=str(s['a'].pk),education_level_id=str(level.pk),capacity=30)
    subject=create(s,'subjects',name='Math',code='MAT')
    section=create(s,'sections',name='A',code='A',branch_id=str(s['a'].pk),school_class_id=str(klass.pk),capacity=20)
    return klass,subject,section

def test_offering_integrity(school):
    s=school;k,sub,sec=structure(s);y=year(s)
    data=dict(name='Math 5',code='M5',branch_id=str(s['a'].pk),academic_year_id=str(y.pk),school_class_id=str(k.pk),subject_id=str(sub.pk),section_id=str(sec.pk))
    row=create(s,'subject-offerings',**data)
    with pytest.raises(ValidationError): create(s,'subject-offerings',**{**data,'code':'M52'})
    with pytest.raises(ValidationError): create(s,'subject-offerings',**{**data,'code':'M53','branch_id':str(s['b'].pk)})
    Service.save('subject-offerings',{'weight':'2'},pk=row.pk,user=s['owner'])
    Service.action('subject-offerings',row.pk,'archive',user=s['owner'])
    Service.action('subject-offerings',row.pk,'restore',user=s['owner'])

def test_filters_permissions(school):
    s=school;structure(s)
    r=s['client'].get('/api/v1/school/classes/?search=Grade&ordering=name&page_size=1')
    assert r.status_code==200 and r.data['data']['count']==1,r.data
    for query in ('page_size=0','page_size=-1','page_size=abc','branch_id=no','ordering=tenant_id'):
        assert s['client'].get('/api/v1/school/classes/?'+query).status_code==400
    s['u'].role=Role.objects.get(slug='school_teacher');s['u'].save()
    assert s['client'].post('/api/v1/school/classes/',{},format='json').status_code==403

def test_campus_crud(school):
    s=school;s['client'].force_authenticate(s['owner'])
    r=s['client'].post('/api/v1/school/campuses/',{'company_id':str(s['c'].pk),'name':'Third','code':'C'},format='json')
    assert r.status_code==201,r.data
    pk=r.data['data']['id']
    assert s['client'].patch(f'/api/v1/school/campuses/{pk}/',{'phone':'123'},format='json').status_code==200
    assert s['client'].delete(f'/api/v1/school/campuses/{pk}/').status_code==200
    assert s['client'].post(f'/api/v1/school/campuses/{pk}/restore/',{},format='json').status_code==200

def test_summary(school):
    r=school['client'].get('/api/v1/school/summary/')
    assert r.status_code==200,r.data
    assert not {'students','fees','attendance_today_pct'} & r.data['data'].keys()

@pytest.mark.parametrize('resource', ['levels','subjects','subject-categories','shifts','classes','sections','subject-offerings','terms'])
def test_complete_resource_http_crud(school,resource):
    s=school;s['client'].force_authenticate(s['owner'])
    k,sub,sec=structure(s);y=year(s)
    data={'name':'Test '+resource,'code':'TEST'}
    if resource in ('shifts','classes','sections','subject-offerings','terms'): data['branch_id']=str(s['a'].pk)
    if resource=='shifts': data.update(start_time='08:00',end_time='12:00')
    if resource=='classes': data['education_level_id']=str(k.education_level_id)
    if resource=='sections': data.update(school_class_id=str(k.pk),capacity=20)
    if resource=='subject-offerings': data.update(academic_year_id=str(y.pk),school_class_id=str(k.pk),subject_id=str(sub.pk))
    if resource=='terms': data.update(academic_year_id=str(y.pk),start_date='2026-09-01',end_date='2026-12-01',sort_order=1)
    url=f'/api/v1/school/{resource}/'
    r=s['client'].post(url,data,format='json');assert r.status_code==201,r.data
    pk=r.data['data']['id'];detail=url+pk+'/'
    assert s['client'].get(detail).status_code==200
    r=s['client'].patch(detail,{'name':'Changed'},format='json');assert r.status_code==200,r.data
    assert s['client'].delete(detail).status_code==200
    assert s['client'].get(detail).status_code==404
    assert s['client'].get(detail+'?archived=true').status_code==200
    r=s['client'].post(detail+'restore/',{},format='json');assert r.status_code==200,r.data

@pytest.mark.parametrize('resource',['classes','sections','shifts','subject-offerings'])
def test_cross_campus_foundation_reads_and_writes(school,resource):
    s=school;k,sub,sec=structure(s);y=year(s)
    if resource=='classes': row=k
    elif resource=='sections':row=sec
    elif resource=='shifts':row=create(s,'shifts',name='Morning',code='AM',branch_id=str(s['a'].pk),start_time='08:00',end_time='12:00')
    else:row=create(s,'subject-offerings',name='Math',code='MATH',branch_id=str(s['a'].pk),academic_year_id=str(y.pk),school_class_id=str(k.pk),subject_id=str(sub.pk))
    s['u'].branch=s['b'];s['u'].save()
    url=f'/api/v1/school/{resource}/{row.pk}/'
    assert s['client'].get(url).status_code==404
    assert s['client'].patch(url,{'name':'Unauthorized'},format='json').status_code==404
    assert s['client'].get(f'/api/v1/school/{resource}/').data['data']['count']==0

def test_cross_tenant_foreign_keys(school):
    s=school;k,sub,sec=structure(s);y=year(s)
    from apps.school.models import Subject,EducationLevel
    foreign_subject=Subject.objects.create(tenant=s['foreign'].tenant,name='Foreign',code='F')
    foreign_level=EducationLevel.objects.create(tenant=s['foreign'].tenant,name='Foreign',code='F')
    for resource,data in [
        ('classes',dict(name='Bad',code='BAD',branch_id=str(s['a'].pk),education_level_id=str(foreign_level.pk))),
        ('subject-offerings',dict(name='Bad',code='BAD',branch_id=str(s['a'].pk),academic_year_id=str(y.pk),school_class_id=str(k.pk),subject_id=str(foreign_subject.pk)))]:
        r=s['client'].post('/api/v1/school/'+resource+'/',data,format='json');assert r.status_code==400,r.data

def test_teacher_cross_campus_and_deactivation(school):
    s=school;k,sub,sec=structure(s)
    teacher=User.objects.create_user(username='teacher',tenant=s['t'],branch=s['b'],role=Role.objects.get(slug='school_teacher'))
    with pytest.raises(ValidationError): Service.save('classes',{'teacher_id':str(teacher.pk)},pk=k.pk,user=s['owner'])
    SchoolCampusAccess.objects.create(tenant=s['t'],user=teacher,branch=s['a'])
    Service.save('classes',{'teacher_id':str(teacher.pk)},pk=k.pk,user=s['owner'])
    teacher.is_active=False;teacher.save()
    k.refresh_from_db();assert k.teacher_id is None
    Service.profile({'branch_id':str(s['a'].pk),'principal_user_id':str(s['u'].pk)},user=s['owner'])
    s['u'].is_active=False;s['u'].save()
    from apps.school.models import SchoolProfile
    assert SchoolProfile.objects.get(branch=s['a']).principal_user_id is None

def test_archive_protection_and_exact_permission_revocation(school):
    s=school;k,sub,sec=structure(s)
    with pytest.raises(ValidationError):Service.action('classes',k.pk,'archive',user=s['owner'])
    from apps.authentication.models import Permission,UserPermission,UserPermissionRevoke
    UserPermission.objects.create(user=s['u'],permission=Permission.objects.get(codename='school.academic.activate'))
    UserPermissionRevoke.objects.create(user=s['u'],permission=Permission.objects.get(codename='school.academic_year.activate'))
    y=year(s)
    assert s['client'].post(f'/api/v1/school/academic-years/{y.pk}/activate/',{},format='json').status_code==403
    assert 'activate' not in s['client'].get('/api/v1/school/capabilities/').data['data']['academic-years']

def test_term_exam_dates_parent_edit_and_overlap_policy(school):
    s=school;y=year(s)
    data=dict(name='T1',code='T1',academic_year_id=str(y.pk),branch_id=str(s['a'].pk),start_date='2026-09-01',end_date='2026-12-01',sort_order=1)
    for bad in ({'exam_start':'2026-11-01'},{'exam_start':'2026-08-01','exam_end':'2026-08-02'},{'sort_order':0},{'end_date':'2027-09-01'}):
        with pytest.raises(ValidationError):create(s,'terms',**{**data,**bad})
    term=create(s,'terms',**data)
    with pytest.raises(ValidationError):Service.save('academic-years',{'start_date':'2026-10-01'},pk=y.pk,user=s['owner'])
    Service.profile({'branch_id':str(s['a'].pk),'allow_term_overlap':True},user=s['owner'])
    create(s,'terms',**{**data,'name':'T2','code':'T2'})
    with pytest.raises(ValidationError):Service.profile({'branch_id':str(s['a'].pk),'allow_term_overlap':False},user=s['owner'])

def test_module_gate_and_no_context(school):
    s=school
    from apps.platform.models import TenantModule
    from rest_framework.exceptions import PermissionDenied
    with pytest.raises(PermissionDenied):Service.save('levels',{'name':'Bad','code':'BAD'})
    TenantModule.objects.filter(tenant=s['t'],module__code='school').update(enabled=False)
    assert s['client'].get('/api/v1/school/levels/').status_code==403
    with pytest.raises(PermissionDenied):create(s,'levels',name='Bad',code='BAD')

def test_year_codes_dates_and_campus_specific_current(school):
    s=school;a=year(s);b=year(s,branch='b',code='B')
    with pytest.raises(ValidationError):year(s,branch='b')
    with pytest.raises(ValidationError):create(s,'academic-years',name='Equal',code='EQ',branch_id=str(s['a'].pk),start_date='2026-01-01',end_date='2026-01-01')
    Service.action('academic-years',a.pk,'activate',user=s['owner']);Service.action('academic-years',b.pk,'activate',user=s['owner'])
    assert AcademicYear.objects.filter(tenant=s['t'],is_current=True).count()==2

def test_profile_restore_validation_and_audit(school):
    s=school
    p=Service.profile({'branch_id':str(s['a'].pk),'display_name':'My School'},user=s['owner'])
    original=p.pk;p.soft_delete(user=s['owner'])
    p=Service.profile({'branch_id':str(s['a'].pk),'display_name':'New name'},user=s['owner'])
    assert p.pk==original and not p.deleted_at
    for bad in ({'timezone':'Not/AZone'},{'currency':'FAKE'},{'attendance_mode':'invalid'},{'tenant_id':str(s['foreign'].tenant_id)}):
        with pytest.raises(ValidationError):Service.profile({'branch_id':str(s['a'].pk),**bad},user=s['owner'])

def test_paginated_lookup_and_default_campus_revocation(school):
    s=school
    r=s['client'].get('/api/v1/school/lookups/campuses/?page_size=1');assert r.data['data']['count']==1
    SchoolCampusAccess.objects.create(tenant=s['t'],user=s['u'],branch=s['a'],is_active=False)
    r=s['client'].get('/api/v1/school/lookups/campuses/');assert r.data['data']['count']==0

@pytest.mark.parametrize('data',[[],None,'bad'])
def test_malformed_json_is_validation_error(school,data):
    r=school['client'].post('/api/v1/school/classes/',data,format='json');assert r.status_code==400,r.data

def test_staff_lookup_does_not_disclose_other_campus(school):
    s=school
    User.objects.create_user(username='Other campus teacher',tenant=s['t'],branch=s['b'],role=Role.objects.get(slug='school_teacher'))
    r=s['client'].get('/api/v1/school/lookups/teachers/',{'branch_id':str(s['a'].pk)})
    assert r.status_code==200,r.data
    assert 'Other campus teacher' not in str(r.data)

def test_year_list_query_count_does_not_grow_per_row(school):
    from django.test.utils import CaptureQueriesContext
    from django.db import connection
    s=school;year(s)
    with CaptureQueriesContext(connection) as small:
        r=s['client'].get('/api/v1/school/academic-years/')
        assert r.status_code==200
    for n in range(10):year(s,code=f'AY-{n}')
    with CaptureQueriesContext(connection) as large:
        r=s['client'].get('/api/v1/school/academic-years/')
        assert r.data['data']['count']==11
    assert len(large)<=len(small)+2

def test_logo_upload_authorization_and_validation(school,tmp_path,settings):
    from django.core.files.uploadedfile import SimpleUploadedFile
    from io import BytesIO
    from PIL import Image
    settings.MEDIA_ROOT=str(tmp_path)
    s=school
    url='/api/v1/school/profile/logo/?branch_id='+str(s['a'].pk)
    assert s['client'].post(url,{'image':SimpleUploadedFile('bad.png',b'not an image',content_type='image/png')},format='multipart').status_code==400
    raw=BytesIO();Image.new('RGB',(4,4),'green').save(raw,format='PNG')
    r=s['client'].post(url,{'image':SimpleUploadedFile('logo.png',raw.getvalue(),content_type='image/png')},format='multipart')
    assert r.status_code==200,r.data
    assert r.data['data']['logo_url']
    r=s['client'].post('/api/v1/school/profile/logo/?branch_id='+str(s['b'].pk),{},format='multipart')
    assert r.status_code==404

@pytest.mark.parametrize('with_term,with_section',[(False,False),(False,True),(True,False),(True,True)])
def test_database_offering_unique_null_scopes(school,with_term,with_section):
    from apps.school.models import SubjectOffering
    s=school;k,sub,sec=structure(s);y=year(s)
    term=create(s,'terms',name='Term',code='T',academic_year_id=str(y.pk),start_date='2026-09-01',end_date='2026-12-01') if with_term else None
    row=create(s,'subject-offerings',name='Offering',code='OFFER',branch_id=str(s['a'].pk),academic_year_id=str(y.pk),school_class_id=str(k.pk),subject_id=str(sub.pk),section_id=str(sec.pk) if with_section else None,term_id=str(term.pk) if term else None)
    with pytest.raises(IntegrityError),transaction.atomic():
        SubjectOffering.objects.create(tenant=s['t'],name='Duplicate',code='DUP',branch=s['a'],academic_year=y,school_class=k,subject=sub,section=sec if with_section else None,term=term)

def test_legacy_url_names_remain(school):
    from django.urls import reverse
    y=year(school)
    assert reverse('school-academic-years').endswith('/school/academic-years/')
    assert reverse('school-academic-year-activate',kwargs={'pk':y.pk}).endswith(f'/{y.pk}/activate/')

@pytest.mark.django_db(transaction=True)
def test_postgresql_concurrent_activation(school):
    from django.db import connection, connections
    if connection.vendor != 'postgresql':
        pytest.skip('PostgreSQL is required to exercise row-level locking.')
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    s=school;a=year(s);b=year(s,code='SECOND');barrier=Barrier(2)
    def activate(pk):
        try:
            actor=User.objects.get(pk=s['owner'].pk)
            barrier.wait(timeout=10)
            Service.action('academic-years',pk,'activate',user=actor)
        finally:
            connections['default'].close()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=[pool.submit(activate,pk) for pk in (a.pk,b.pk)]
        for result in results:result.result(timeout=30)
    assert AcademicYear.objects.filter(tenant=s['t'],branch=s['a'],is_current=True).count()==1
