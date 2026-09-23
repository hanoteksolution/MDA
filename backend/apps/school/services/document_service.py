"""Document verification and acceptance gates."""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from apps.school.models import AdmissionDocumentType, ApplicantDocument, StudentDocument
from .sis_common import get, invalid, lock, persist, reason, event


def missing_documents(application, access, *, school_class=None, branch=None):
    school_class = school_class or application.school_class
    branch = branch or application.branch
    required = AdmissionDocumentType.objects.filter(tenant=access.tenant, required=True, status='active', deleted_at__isnull=True).filter(Q(branch__isnull=True)|Q(branch=branch)).filter(Q(school_class__isnull=True)|Q(school_class=school_class)).filter(Q(education_level__isnull=True)|Q(education_level=school_class.education_level))
    valid = application.documents.filter(deleted_at__isnull=True, verification_status='verified', file__deleted_at__isnull=True).filter(Q(expiry_date__isnull=True)|Q(expiry_date__gte=timezone.localdate())).values('document_type_id')
    return required.exclude(pk__in=valid)


def require_documents(application, access, data, **placement):
    missing = list(missing_documents(application, access, **placement).values_list('name', flat=True))
    if not missing:return ''
    if not data.get('document_override_reason'):invalid('documents', 'Missing verified required documents: '+', '.join(missing))
    access.require('admission', 'override_document_requirement')
    value = reason(data, 'document_override_reason')
    event(application, access, 'document_requirement_overridden', reason=value, missing=missing)
    return value


@transaction.atomic
def verify(resource, pk, data, *, access):
    access.require('admission_document' if resource=='applicant-documents' else 'student_document', 'verify')
    lock(access)
    row = get(access, ApplicantDocument if resource=='applicant-documents' else StudentDocument, pk)
    target = data.get('verification_status')
    if target not in ('verified','rejected','expired','requires_reupload'):invalid('verification_status', 'Choose a verification outcome.')
    if target=='verified' and row.expiry_date and row.expiry_date<timezone.localdate():invalid('expiry_date', 'Expired documents cannot be verified.')
    if target!='verified':reason(data)
    row.verification_status=target;row.verified_by=access.user;row.verified_at=timezone.now()
    persist(row,access,'document_'+target)
    event(row,access,'document_verification_reason',reason=data.get('reason',''))
    return row
