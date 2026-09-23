"""Disposable browser fixtures only. Run with explicitly isolated verification settings."""
import json
from pathlib import Path
from django.conf import settings
from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from apps.authentication.models import User, Role
from apps.platform.models import Tenant, BusinessType
from apps.platform.services.module_service import sync_tenant_modules
from apps.settings_app.models import Company, Branch
from rest_framework_simplejwt.tokens import RefreshToken

assert settings.DATABASES['default']['NAME'] == 'school_verify', 'Use the disposable verification database.'
bootstrap_roles_and_permissions()
business, _ = BusinessType.objects.get_or_create(code='school', defaults={'name':'School'})
output = {'users': {}}
for label in ('A','B'):
    tenant, _ = Tenant.objects.get_or_create(slug=f'browser-school-{label.lower()}', defaults={'name':f'Browser School {label}', 'business_type':business, 'status':'active', 'currency':'USD'})
    sync_tenant_modules(tenant=tenant, enabled_codes=['school','sales','inventory'])
    company, _ = Company.objects.get_or_create(tenant=tenant, name=f'Browser School {label}')
    for number in (1,2) if label == 'A' else (1,):
        branch, _ = Branch.objects.get_or_create(tenant=tenant, company=company, code=f'{label}{number}', defaults={'name':f'Campus {label}{number}'})
        output[f'campus_{label}{number}'] = str(branch.pk)
        for role in ('owner','principal','teacher') if label=='A' and number==1 else ('principal',):
            user, _ = User.objects.get_or_create(username=f'browser_{label}{number}_{role}', defaults={'tenant':tenant,'branch':branch,'role':Role.objects.get(slug=f'school_{role}')})
            user.set_password('LocalVerificationOnly123!'); user.save()
            refresh=RefreshToken.for_user(user)
            output['users'][f'{label}{number}_{role}']={'access':str(refresh.access_token),'refresh':str(refresh)}
    output[f'company_{label}']=str(company.pk)
Path('/tmp/school25-browser-session.json').write_text(json.dumps(output))
print('Created isolated School browser fixtures; tokens stored only in /tmp.')
