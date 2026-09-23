"""Authoritative relations and master-data safeguards for student services."""
import re
from django.db.models import Q
from django.utils import timezone
from apps.school.models import *
from .sis_common import get, invalid, staff
from .ops_integrity import validate_ops, can_archive_ops


def validate(row,access):
    if getattr(row,'branch_id',None):access.campus(row.branch_id)
    for field in row._meta.fields:
        if not field.is_relation or field.name in ('tenant','branch','created_by','updated_by','deleted_by'):continue
        pk=getattr(row,field.attname)
        if not pk:continue
        if field.related_model._meta.app_label=='authentication':
            if field.name=='assigned_reviewer':staff(access,pk,row.branch,'review')
            continue
        if field.related_model is SchoolFile:
            # Campus access alone must not let a guessed file ID acquire a new
            # readable attachment through a different resource's permissions.
            from .private_files import download
            related,_=download(pk,access=access)
            if field.name=='photo' and not related.content_type.startswith('image/'):
                invalid(field.attname,'Choose an image for the identity photo.')
        else:
            related=get(access,field.related_model,pk,field.attname)
        if getattr(related,'status','active') in ('archived','inactive'):
            invalid(field.attname,'Choose an active related record.')
        if field.name in ('academic_year','school_class','section','desired_year','desired_class','desired_section') and getattr(related,'branch_id',row.branch_id)!=row.branch_id:
            invalid(field.attname,'Related record belongs to another campus.')
    if hasattr(row,'date_of_birth') and row.date_of_birth>timezone.localdate():invalid('date_of_birth','Birth date cannot be in the future.')
    if isinstance(row,Applicant) and row.desired_section_id and row.desired_section.school_class_id!=row.desired_class_id:
        invalid('desired_section_id','Section does not belong to the desired class.')
    if isinstance(row,AdmissionApplication):
        if row.applicant.branch_id!=row.branch_id:invalid('applicant_id','Applicant and application must belong to the same campus.')
        if row.academic_year.status not in ('planning','active'):invalid('academic_year_id','Academic year is closed.')
        if row.section_id and row.section.school_class_id!=row.school_class_id:invalid('section_id','Section does not belong to the requested class.')
    if isinstance(row,(StudentGuardian,ApplicantGuardian)):
        parent=row.student if isinstance(row,StudentGuardian) else row.applicant
        if row.branch_id!=parent.branch_id:invalid('branch_id','Relationship must use the child campus.')
        if row.is_primary and row.status=='active' and row.end_date and row.end_date<timezone.localdate():invalid('end_date','An expired relationship cannot remain primary and active.')
    if isinstance(row,StudentNote) and row.category=='confidential':access.require('student_note_confidential','update')
    if isinstance(row,SchoolAdmissionPolicy):
        clean=row.student_prefix.replace('{year}','').replace('{campus}','')
        if not row.student_prefix or not re.fullmatch(r'[A-Za-z0-9 _./-]*',clean):invalid('student_prefix','Use literal letters/numbers and optional {year}/{campus} tokens.')
    if isinstance(row,AdmissionDocumentType):
        if not isinstance(row.allowed_types,list) or any(v not in ('application/pdf','image/png','image/jpeg','image/webp') for v in row.allowed_types):invalid('allowed_types','Choose supported PDF/image MIME types.')
        if row.school_class_id and row.education_level_id and row.school_class.education_level_id!=row.education_level_id:invalid('education_level_id','Class and level do not match.')
    validate_ops(row,access)
    if isinstance(row,(ApplicantDocument,StudentDocument)):
        if row.document_type.branch_id and row.document_type.branch_id!=row.branch_id:invalid('document_type_id','Document requirement belongs to another campus.')
        if row.document_type.expiry_required and not row.expiry_date:invalid('expiry_date','This document type requires an expiry date.')
        if row.file.size>row.document_type.max_size_mb*1024*1024:invalid('file_id','Document exceeds this requirement’s size limit.')
        if row.document_type.allowed_types and row.file.content_type not in row.document_type.allowed_types:invalid('file_id','File type is not permitted by this document requirement.')


def can_archive(row,access):
    can_archive_ops(row)
    if isinstance(row,Student):
        if row.enrollments.filter(status__in=['active','pending'],deleted_at__isnull=True).exists():invalid('status','Withdraw or complete the active enrollment before archiving.')
        return
    for rel in row._meta.related_objects:
        if rel.related_model._meta.app_label!='school':continue
        qs=rel.related_model.objects.filter(**{rel.field.name:row},deleted_at__isnull=True)
        if qs.exists():invalid('status',f'Reassign or archive related {rel.related_model._meta.verbose_name_plural} first.')
