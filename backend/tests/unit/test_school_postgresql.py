"""Phase 2 release gates: execute against PostgreSQL, never emulate locks in SQLite."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
import pytest
from django.db import connection, connections, transaction, IntegrityError
from rest_framework.test import APIClient
from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import User, Role
from apps.platform.models import Tenant
from apps.platform.services.module_service import sync_tenant_modules
from apps.settings_app.models import Company, Branch
from apps.school.models import AcademicYear, AcademicTerm, SchoolProfile, SubjectOffering
from apps.school.repositories.foundation import MODELS
from apps.school.services.foundation_service import FoundationService as Service

pytestmark = pytest.mark.django_db(transaction=True)

@pytest.fixture
def setup_school():
    if connection.vendor != 'postgresql':
        pytest.skip('Requires real PostgreSQL transactions and catalog.')
    bootstrap_roles_and_permissions()
    tenant = Tenant.objects.create(name='Concurrency school', slug='concurrent-school', currency='USD')
    sync_tenant_modules(tenant=tenant, enabled_codes=['school', 'sales', 'inventory'])
    company = Company.objects.create(tenant=tenant, name='School')
    branch = Branch.objects.create(tenant=tenant, company=company, name='Campus A', code='A')
    owner = User.objects.create_user(username='owner', tenant=tenant, branch=branch, role=Role.objects.get(slug='school_owner'))
    def create(resource, **values):
        return Service.save(resource, values, user=owner)
    year = create('academic-years', name='Year', code='YEAR', branch_id=str(branch.pk), start_date='2026-01-01', end_date='2026-12-31')
    level = create('levels', name='Primary', code='PRIMARY')
    klass = create('classes', name='Grade 1', code='G1', branch_id=str(branch.pk), education_level_id=str(level.pk))
    subject = create('subjects', name='Math', code='MATH')
    section = create('sections', name='Stream A', code='SA', branch_id=str(branch.pk), school_class_id=str(klass.pk))
    return dict(tenant=tenant, company=company, branch=branch, owner=owner, year=year, level=level, klass=klass, subject=subject, section=section, create=create)


def race(user, requests):
    barrier = Barrier(len(requests))
    def send(request):
        try:
            actor = User.objects.get(pk=user.pk)
            client = APIClient(); client.force_authenticate(actor)
            barrier.wait(timeout=15)
            response = client.post(request[0], request[1], format='json')
            return response.status_code, response.data
        finally:
            connections['default'].close()
    with ThreadPoolExecutor(max_workers=len(requests)) as pool:
        futures = [pool.submit(send, request) for request in requests]
        return [future.result(timeout=45) for future in futures]


def test_concurrent_current_year_api(setup_school):
    s = setup_school
    other = s['create']('academic-years', name='Next', code='NEXT', branch_id=str(s['branch'].pk), start_date='2027-01-01', end_date='2027-12-31')
    responses = race(s['owner'], [(f'/api/v1/school/academic-years/{year.pk}/make-current/', {}) for year in [s['year'], other]])
    assert [code for code, _ in responses] == [200, 200], responses
    assert AcademicYear.objects.filter(tenant=s['tenant'], branch=s['branch'], is_current=True).count() == 1
    with connection.cursor() as cursor:
        cursor.execute('SHOW transaction_isolation')
        assert cursor.fetchone()[0] == 'read committed'


@pytest.mark.parametrize('resource', ['academic-years', 'campuses', 'classes', 'subjects', 'sections', 'subject-offerings'])
def test_concurrent_unique_creates(setup_school, resource):
    s = setup_school
    payload = dict(name='Concurrent', code='CONCURRENT')
    payload.update({
        'academic-years': dict(branch_id=str(s['branch'].pk), start_date='2027-01-01', end_date='2027-12-31'),
        'campuses': dict(company_id=str(s['company'].pk)),
        'classes': dict(branch_id=str(s['branch'].pk), education_level_id=str(s['level'].pk)),
        'subjects': {},
        'sections': dict(branch_id=str(s['branch'].pk), school_class_id=str(s['klass'].pk)),
        'subject-offerings': dict(branch_id=str(s['branch'].pk), academic_year_id=str(s['year'].pk), school_class_id=str(s['klass'].pk), subject_id=str(s['subject'].pk)),
    }[resource])
    second = dict(payload)
    # Exercise offering scope and section identity independently from code uniqueness.
    if resource in ('subject-offerings', 'sections'):
        second['code'] = 'DIFFERENT'
    responses = race(s['owner'], [(f'/api/v1/school/{resource}/', data) for data in [payload, second]])
    assert sorted(code for code, _ in responses) == [201, 400], responses
    assert MODELS[resource].objects.filter(tenant=s['tenant'], name='Concurrent').count() == 1
    assert 'IntegrityError' not in str(responses)


@pytest.mark.parametrize('operation', ['current', 'term_activate', 'term_close', 'principal', 'offering', 'archive'])
def test_audit_failure_rolls_back_entire_workflow(setup_school, operation):
    s = setup_school
    Service.action('academic-years', s['year'].pk, 'activate', user=s['owner'])
    other = s['create']('academic-years', name='Next', code='NEXT', branch_id=str(s['branch'].pk), start_date='2027-01-01', end_date='2027-12-31')
    term = s['create']('terms', name='Term', code='TERM', academic_year_id=str(s['year'].pk), start_date='2026-01-01', end_date='2026-04-01')
    actions = {
        'current': lambda: Service.action('academic-years', other.pk, 'activate', user=s['owner']),
        'term_activate': lambda: Service.action('terms', term.pk, 'activate', user=s['owner']),
        'term_close': lambda: Service.action('terms', term.pk, 'close', user=s['owner']),
        'principal': lambda: Service.profile({'branch_id': str(s['branch'].pk), 'principal_user_id': str(s['owner'].pk)}, user=s['owner']),
        'offering': lambda: s['create']('subject-offerings', name='Offering', code='OFFER', branch_id=str(s['branch'].pk), academic_year_id=str(s['year'].pk), school_class_id=str(s['klass'].pk), subject_id=str(s['subject'].pk)),
        'archive': lambda: Service.action('subjects', s['subject'].pk, 'archive', user=s['owner']),
    }
    with patch('apps.school.services.foundation_service.write_audit', side_effect=RuntimeError('Injected audit failure')):
        with pytest.raises(RuntimeError, match='Injected audit failure'):
            actions[operation]()
    s['year'].refresh_from_db(); other.refresh_from_db(); term.refresh_from_db(); s['subject'].refresh_from_db()
    assert s['year'].is_current and not other.is_current
    assert term.status == 'planning'
    assert not SchoolProfile.objects.filter(tenant=s['tenant']).exists()
    assert not SubjectOffering.objects.filter(tenant=s['tenant']).exists()
    assert s['subject'].deleted_at is None


def test_postgresql_catalog_and_fk_checks(setup_school):
    s = setup_school
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, SubjectOffering._meta.db_table)
        for suffix in ('00', '01', '10', '11'):
            assert constraints[f'school_offering_scope_{suffix}']['unique']
        assert constraints['school_offering_marks']['check']
        assert any(item['foreign_key'] for item in constraints.values())
        cursor.execute('SELECT indexdef FROM pg_indexes WHERE tablename = %s', [SubjectOffering._meta.db_table])
        definitions = '\n'.join(row[0] for row in cursor.fetchall())
        assert 'WHERE' in definitions and 'IS NULL' in definitions and 'IS NOT NULL' in definitions
    with pytest.raises(IntegrityError), transaction.atomic():
        # Bypass service validation to prove the database itself rejects invalid marks.
        s['subject'].maximum_marks = -1
        s['subject'].save()
    with pytest.raises(IntegrityError), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(f'DELETE FROM {s["level"]._meta.db_table} WHERE id = %s', [s['level'].pk])
            cursor.execute('SET CONSTRAINTS ALL IMMEDIATE')


def test_real_database_campus_and_tenant_request_matrix(setup_school):
    s=setup_school
    second=Branch.objects.create(tenant=s['tenant'],company=s['company'],code='A2',name='Campus A2')
    other=Tenant.objects.create(name='Tenant B',slug='tenant-b',currency='USD')
    sync_tenant_modules(tenant=other,enabled_codes=['school','sales','inventory'])
    company=Company.objects.create(tenant=other,name='Company B')
    foreign=Branch.objects.create(tenant=other,company=company,code='B1',name='Campus B1')
    principals=[User.objects.create_user(username=f'principal-{i}',tenant=branch.tenant,branch=branch,role=Role.objects.get(slug='school_principal')) for i,branch in enumerate([s['branch'],second,foreign])]
    foreign_year=Service.save('academic-years',dict(name='B year',code='B',branch_id=str(foreign.pk),start_date='2026-01-01',end_date='2026-12-31'),user=principals[2])
    second_year=s['create']('academic-years',name='A2 year',code='A2',branch_id=str(second.pk),start_date='2026-01-01',end_date='2026-12-31')
    for actor, forbidden in [(principals[0],second_year),(principals[0],foreign_year),(principals[1],s['year']),(s['owner'],foreign_year)]:
        client=APIClient();client.force_authenticate(actor)
        url=f'/api/v1/school/academic-years/{forbidden.pk}/'
        for method,payload in [('get',None),('patch',{'name':'Forbidden'}),('delete',None)]:
            response=getattr(client,method)(url,payload,format='json')
            assert response.status_code==404,(actor.username,method,response.data)
        for command in ['activate','close','archive','restore']:
            assert client.post(url+command+'/',{},format='json').status_code==404
        response=client.post('/api/v1/school/terms/',{'name':'Forbidden','code':'NO','academic_year_id':str(forbidden.pk),'branch_id':str(forbidden.branch_id),'start_date':'2026-01-01','end_date':'2026-03-01'},format='json')
        assert response.status_code in (400,404)
    client=APIClient();client.force_authenticate(principals[0])
    url='/api/v1/school/profile/'
    assert client.put(url,{'branch_id':str(s['branch'].pk),'principal_user_id':str(principals[0].pk)},format='json').status_code==200
    for person in [principals[1],principals[2]]:
        assert client.put(url,{'branch_id':str(s['branch'].pk),'principal_user_id':str(person.pk)},format='json').status_code==400
    principals[0].is_active=False;principals[0].save()
    assert SchoolProfile.objects.get(branch=s['branch']).principal_user_id is None
    client.force_authenticate(s['owner'])
    assert client.put(url,{'branch_id':str(s['branch'].pk),'principal_user_id':str(principals[0].pk)},format='json').status_code==400
