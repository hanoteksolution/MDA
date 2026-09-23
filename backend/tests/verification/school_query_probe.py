"""Representative PostgreSQL query evidence on isolated synthetic tenants."""
import json
from pathlib import Path
from datetime import date
from django.conf import settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient
from apps.authentication.models import User, Role
from apps.platform.models import Tenant
from apps.platform.services.module_service import sync_tenant_modules
from apps.settings_app.models import Company, Branch
from apps.school.models import EducationLevel, SchoolClass, Section, Subject, SubjectOffering, AcademicYear, AcademicTerm
from apps.school.policies.access import SchoolAccess
from apps.school.repositories.foundation import queryset
assert connection.vendor == 'postgresql' and settings.DATABASES['default']['NAME']=='school_verify'
actors=[]
for number in range(3):
    tenant, fresh=Tenant.objects.get_or_create(slug=f'query-school-{number}',defaults={'name':f'Query school {number}','currency':'USD'})
    sync_tenant_modules(tenant=tenant,enabled_codes=['school','sales','inventory'])
    company,_=Company.objects.get_or_create(tenant=tenant,name='Query school')
    if fresh:
        levels=EducationLevel.objects.bulk_create([EducationLevel(tenant=tenant,name=f'Level {i}',code=f'L{i}') for i in range(12)])
        subjects=Subject.objects.bulk_create([Subject(tenant=tenant,name=f'Subject {i}',code=f'S{i}') for i in range(45)])
        for campus in range(3):
            branch=Branch.objects.create(tenant=tenant,company=company,name=f'Campus {campus}',code=f'C{campus}')
            years=AcademicYear.objects.bulk_create([AcademicYear(tenant=tenant,branch=branch,name=f'Year {i}',code=f'C{campus}Y{i}',start_date=date(2020+i,1,1),end_date=date(2020+i,12,31)) for i in range(5)])
            AcademicTerm.objects.bulk_create([AcademicTerm(tenant=tenant,branch=branch,academic_year=y,name=f'Term {i}',code=f'T{i}',sort_order=i,start_date=date(y.start_date.year,1+(i-1)*4,1),end_date=date(y.start_date.year,i*4,1)) for y in years for i in range(1,4)])
            classes=SchoolClass.objects.bulk_create([SchoolClass(tenant=tenant,branch=branch,education_level=levels[i],name=f'Class {i}',code=f'K{i}') for i in range(12)])
            Section.objects.bulk_create([Section(tenant=tenant,branch=branch,school_class=k,name=f'Section {j}',code=f'SEC{j}') for k in classes for j in range(3)])
            SubjectOffering.objects.bulk_create([SubjectOffering(tenant=tenant,branch=branch,academic_year=years[0],school_class=k,subject=sub,name=f'{k.name} {sub.name}',code=f'{k.code}{sub.code}') for k in classes for sub in subjects[:30]])
    branch=Branch.objects.filter(tenant=tenant).first()
    actor,_=User.objects.get_or_create(username=f'query_owner_{number}',defaults={'tenant':tenant,'branch':branch,'role':Role.objects.get(slug='school_owner')})
    actors.append(actor)
actor=actors[0];client=APIClient();client.force_authenticate(actor)
report={'dataset':{'tenants':3,'campuses':9,'years':45,'terms':135,'levels':36,'classes':108,'sections':324,'subjects':135,'offerings':3240},'pages':{}}
for resource in ['academic-years','terms','classes','sections','subjects','subject-offerings','campuses']:
    counts=[]
    for size in [1,25]:
        with CaptureQueriesContext(connection) as queries:
            response=client.get(f'/api/v1/school/{resource}/',{'page_size':size,'ordering':'name'})
            assert response.status_code==200,response.data
        counts.append(len(queries))
    assert counts[1] <= counts[0]+2,(resource,counts)
    first=client.get(f'/api/v1/school/{resource}/',{'page_size':2,'ordering':'name'}).data['data']['results']
    repeat=client.get(f'/api/v1/school/{resource}/',{'page_size':2,'ordering':'name'}).data['data']['results']
    second=client.get(f'/api/v1/school/{resource}/',{'page_size':2,'ordering':'name','page':2}).data['data']['results']
    assert [r['id'] for r in first]==[r['id'] for r in repeat]
    assert not set(r['id'] for r in first)&set(r['id'] for r in second)
    qs=queryset(resource,SchoolAccess(user=actor)).order_by('name','pk')[:25]
    report['pages'][resource]={'query_counts_1_25':counts,'plan':json.loads(qs.explain(format='json',analyze=True,buffers=True))}
Path('/tmp/school25-query-report.json').write_text(json.dumps(report,indent=2,default=str))
print(json.dumps({key:value['query_counts_1_25'] for key,value in report['pages'].items()}))
