"""Shared lifecycle validation, locks, numbering and redacted audit."""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError, NotFound
from apps.school.models import SchoolAdmissionPolicy, SchoolSequence, Student, Applicant, Guardian, AdmissionApplication
from apps.school.services.foundation_service import save_validated
from apps.school.serializers.sis import serialize
from apps.audit.services import write_audit


def invalid(field, message):
    raise ValidationError({field:message})


def lock(access):
    type(access.tenant).objects.select_for_update().get(pk=access.tenant.pk)


def get(access, model, pk, field='id', *, archived=False):
    from rest_framework import serializers
    pk=serializers.UUIDField().run_validation(pk)
    row=access.scope(model.objects.all()).filter(pk=pk,deleted_at__isnull=not archived).first()
    if row is None:
        raise NotFound(f'{field}: record not found in the permitted campus/tenant scope.')
    return row


def policy(access, branch):
    return SchoolAdmissionPolicy.objects.filter(tenant=access.tenant,branch=branch,deleted_at__isnull=True).first() or SchoolAdmissionPolicy(tenant=access.tenant,branch=branch)


def persist(row, access, action, before=None):
    if before is None and not row._state.adding:
        previous = type(row).objects.get(pk=row.pk)
        before = serialize(previous, audit=True)
    if row._state.adding:row.created_by=access.user
    row.updated_by=access.user
    save_validated(row)
    write_audit(module='school',action=action,entity=row,user=access.user,request=access.request,old_values=before or {},new_values=serialize(row,audit=True))
    return row


def event(row,access,action,**details):
    write_audit(module='school',action=action,entity=row,user=access.user,request=access.request,new_values=details)


def number(access, kind, branch, year=None):
    """Called under the tenant lock; IDs stay unique across scoped counters."""
    config=policy(access,branch)
    scope='tenant'
    if kind=='student':
        scope=':'.join([str(branch.pk) if 'campus' in config.number_scope else '',str(year.pk) if year and 'year' in config.number_scope else '']) or 'tenant'
    counter,_=SchoolSequence.objects.get_or_create(tenant=access.tenant,kind=kind,scope_key=scope,defaults={'branch':branch,'created_by':access.user})
    model={'student':Student,'applicant':Applicant,'guardian':Guardian,'application':AdmissionApplication}[kind]
    prefix=config.student_prefix if kind=='student' else {'applicant':'APP-','application':'ADM-','guardian':'GUA-'}[kind]
    prefix=prefix.replace('{year}',str(year.start_date.year if year else timezone.localdate().year)).replace('{campus}',branch.code)
    for _ in range(10000):
        counter.last_value+=1
        value=f'{prefix}{counter.last_value:0{config.student_padding if kind=="student" else 6}d}'
        if len(value)>60:invalid('student_prefix','Generated number exceeds 60 characters.')
        if not model.objects.filter(tenant=access.tenant,number=value).exists():
            counter.save(update_fields=['last_value','updated_at'])
            return value
    invalid('number','Sequence exhausted; review the numbering configuration.')


def staff(access,pk,branch,action):
    from apps.authentication.models import User
    person=User.objects.filter(pk=pk,tenant=access.tenant,is_active=True,deleted_at__isnull=True).first()
    if not person or not person.has_permission(f'school.admission.{action}'):
        invalid('assigned_reviewer_id','Choose active staff with the required admissions permission.')
    from apps.school.repositories.sis import StudentAccess
    StudentAccess(user=person).campus(branch.pk)
    return person


def reason(data, field='reason'):
    value=str(data.get(field,'')).strip()
    if not value:invalid(field,'A reason is required.')
    return value


def date_value(data,field,default=None):
    from rest_framework import serializers
    return serializers.DateField().run_validation(data.get(field,default))
