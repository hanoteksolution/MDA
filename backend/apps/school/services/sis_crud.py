"""Master CRUD; dedicated services handle every irreversible lifecycle command."""
from django.db import transaction
from django.utils import timezone
from apps.school.models import *
from apps.school.sis_permissions import RESOURCES
from apps.school.repositories.sis import MODELS, StudentAccess, queryset
from apps.school.serializers.sis import validate_input, serialize
from .sis_common import lock, get, invalid, number, persist
from .sis_integrity import validate, can_archive

IMMUTABLE = ('branch_id','student_id','applicant_id','application_id','academic_year_id','school_class_id','guardian_id','employee_id','staff_id','version_id')
READ_ONLY = ('decisions','transitions','attendance-sessions','attendance-records','attendance-corrections')


class StudentCrudService:
    @staticmethod
    @transaction.atomic
    def save(resource,data,*,access,pk=None):
        from apps.school.fee_contracts import MODELS as FEES
        if resource in FEES:
            from .fee_crud import FeeCrud
            return FeeCrud.save(resource,data,access=access,pk=pk)
        from apps.school.learning_contracts import MODELS as LEARNING
        if resource in LEARNING:
            from .learning_crud import LearningCrud
            return LearningCrud.save(resource,data,access=access,pk=pk)
        access.require(RESOURCES[resource],'update' if pk else 'create')
        if resource in READ_ONLY or (resource=='students' and not pk) or resource=='enrollments':
            invalid('action','Use the dedicated workflow command.')
        lock(access)
        row=get(access,MODELS[resource],pk) if pk else MODELS[resource](tenant=access.tenant)
        before=serialize(row,audit=True) if pk else {}
        if isinstance(row,AdmissionApplication) and row.status not in ('draft','document_review','under_review'):
            invalid('status','This application cannot be edited in its current state.')
        if isinstance(row,(AdmissionAssessment,AdmissionInterview)) and pk:invalid('action','Use complete, cancel or reschedule commands.')
        if isinstance(row,(ApplicantDocument,StudentDocument)) and row.verification_status=='verified':invalid('action','Verified documents are immutable; upload a replacement.')
        if isinstance(row,StudentNote) and row.category=='confidential':access.require('student_note_confidential','update')
        values=validate_input(resource,data,partial=bool(pk))
        for key,value in values.items():
            if pk and key in IMMUTABLE and str(value)!=str(getattr(row,key,None)):invalid(key,'This relationship is immutable; use a workflow.')
            if key=='status' and value=='archived':invalid(key,'Use Archive.')
            setattr(row,key,value)
        from .ops_integrity import prepare
        prepare(row,access)
        for parent_field in ('student','application','applicant'):
            if hasattr(row,parent_field+'_id') and getattr(row,parent_field+'_id') and resource not in ('students','applications'):
                parent=get(access,row._meta.get_field(parent_field).related_model,getattr(row,parent_field+'_id'))
                row.branch=parent.branch
                break
        if isinstance(row,(Applicant,Guardian)) and not pk:
            row.number=number(access,'applicant' if isinstance(row,Applicant) else 'guardian',access.campus(row.branch_id))
        if isinstance(row,AdmissionApplication) and not pk:
            row.number=number(access,'application',access.campus(row.branch_id))
        if isinstance(row,(AdmissionAssessment,AdmissionInterview)):
            from .admission_workflow import schedule
            return schedule(row,access)
        validate(row,access)
        return persist(row,access,'create' if not pk else 'update',before)

    @staticmethod
    @transaction.atomic
    def archive(resource,pk,*,access,restore=False):
        from apps.school.fee_contracts import MODELS as FEES
        if resource in FEES:invalid('action','Financial history cannot be archived; use a financial command.')
        from apps.school.learning_contracts import MODELS as LEARNING
        if resource in LEARNING:invalid('action','Academic history cannot be archived through CRUD.')
        access.require(RESOURCES[resource],'restore' if restore else 'archive')
        if resource in READ_ONLY or resource in ('enrollments','assessments','interviews'):
            invalid('action','Historical records use lifecycle commands, not archive.')
        lock(access);row=get(access,MODELS[resource],pk,archived=restore);before=serialize(row,audit=True)
        if isinstance(row,AdmissionApplication) and row.status not in ('draft','cancelled','withdrawn','rejected'):
            invalid('status','Only draft or terminated applications may be archived.')
        if isinstance(row,StudentNote) and row.category=='confidential':access.require('student_note_confidential','update')
        if restore:
            row.deleted_at=row.deleted_by=None
            if isinstance(row,Student):row.status='inactive'
            elif hasattr(row,'status') and row.status=='archived':row.status='inactive'
            validate(row,access)
        else:
            can_archive(row,access)
            row.deleted_at=timezone.now();row.deleted_by=access.user
            if hasattr(row,'status') and not isinstance(row,AdmissionApplication):row.status='archived'
        return persist(row,access,'restore' if restore else 'archive',before)
