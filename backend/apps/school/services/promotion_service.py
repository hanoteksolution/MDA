"""Persisted, stale-safe promotion preview and atomic idempotent commit."""
import hashlib,json
from collections import Counter
from datetime import timedelta
from django.db import transaction
from django.utils import timezone
from apps.school.models import AcademicYear, SchoolClass, Section, StudentEnrollment, StudentTransition
from apps.school.models.learning import ResultPublication, PromotionBatch, PromotionItem
from .sis_common import get,invalid,lock,persist,reason,date_value
from .enrollment_service import placement


def inspect(batch,items,access):
    publication=get(access,ResultPublication,batch.publication_id)
    exam=publication.exam
    if exam.status!='published' or exam.publications.order_by('-version').first().pk!=publication.pk:invalid('publication_id','Preview requires the current published results.')
    if batch.effective_date>timezone.localdate():invalid('effective_date','Execute promotion when it takes effect; future scheduling is not supported.')
    results={r['enrollment_id']:r for r in publication.snapshot['students']}
    stamp={'publication':str(publication.pk),'exam_revision':exam.revision,'effective':str(batch.effective_date),'items':[]}
    year=None
    if batch.target_year_id:
        year=get(access,AcademicYear,batch.target_year_id)
        if year.branch_id!=batch.branch_id or year.status!='active' or not year.enrollment_open or year.start_date<=exam.academic_year.start_date or not year.start_date<=batch.effective_date<=timezone.localdate()<=year.end_date:invalid('target_year_id','Choose an open, active later year in this campus covering the effective date and today.')
        stamp['year']=[str(year.pk),str(year.updated_at)]
    class_counts=Counter();section_counts=Counter();seen=set()
    for item in items:
        e=get(access,StudentEnrollment,item.enrollment_id)
        if e.pk in seen:invalid('items','An enrollment appears twice.')
        seen.add(e.pk)
        result=results.get(str(e.pk))
        if not result or e.branch_id!=batch.branch_id or e.status!='active' or e.student.status!='active' or e.student.deleted_at or e.student.branch_id!=batch.branch_id or batch.effective_date<=e.start_date:invalid('enrollment_id','Select an active enrollment from this publication; effective date must follow its start.')
        if item.outcome not in ('promote','repeat','graduate'):invalid('outcome','Choose promote, repeat or graduate.')
        if item.outcome in ('promote','graduate') and not result['passed']:invalid('outcome','Only passing published results may promote or graduate; use repetition for failed results.')
        facts=[str(e.pk),e.status,str(e.updated_at),str(e.student.updated_at),item.outcome]
        if item.outcome=='graduate':
            if item.target_class_id or item.target_section_id:invalid('target_class_id','Graduation has no destination placement.')
        else:
            if not year:invalid('target_year_id','Promotion/repetition requires a target year.')
            klass=get(access,SchoolClass,item.target_class_id)
            if klass.branch_id!=batch.branch_id or klass.status!='active':invalid('target_class_id','Choose an active class in this campus; use transfer for campus changes.')
            if (item.outcome=='repeat')!=(klass.pk==e.school_class_id):invalid('target_class_id','Repetition keeps the class; promotion requires a different class.')
            class_counts[klass.pk]+=1
            occupied=StudentEnrollment.objects.filter(academic_year=year,school_class=klass,status='active',deleted_at__isnull=True).count()
            if occupied+class_counts[klass.pk]>klass.capacity:invalid('capacity','Destination class cannot accommodate this batch.')
            facts.extend([str(klass.pk),str(klass.updated_at),occupied])
            if item.target_section_id:
                section=get(access,Section,item.target_section_id)
                if section.school_class_id!=klass.pk or section.status!='active':invalid('target_section_id','Choose an active section in the destination class.')
                section_counts[section.pk]+=1
                count=StudentEnrollment.objects.filter(academic_year=year,section=section,status='active',deleted_at__isnull=True).count()
                if count+section_counts[section.pk]>section.capacity:invalid('capacity','Destination section cannot accommodate this batch.')
                facts.extend([str(section.pk),str(section.updated_at),count])
        stamp['items'].append(facts)
    return hashlib.sha256(json.dumps(stamp,sort_keys=True).encode()).hexdigest()


@transaction.atomic
def preview(data,*,access):
    access.require('promotion','preview');lock(access)
    pub=get(access,ResultPublication,data.get('publication_id'))
    batch=PromotionBatch(tenant=access.tenant,branch=pub.branch,publication=pub,target_year_id=data.get('target_year_id') or None,effective_date=date_value(data,'effective_date'),reason=reason(data))
    if batch.target_year_id:batch.target_year=get(access,AcademicYear,batch.target_year_id)
    values=data.get('items')
    if not isinstance(values,list) or not 1<=len(values)<=500:invalid('items','Preview 1–500 students at a time.')
    items=[]
    for value in values:
        if not isinstance(value,dict) or set(value)-{'enrollment_id','target_class_id','target_section_id','outcome'}:invalid('items','Unsupported promotion item.')
        e=get(access,StudentEnrollment,value.get('enrollment_id'))
        klass=get(access,SchoolClass,value['target_class_id']) if value.get('target_class_id') else None
        section=get(access,Section,value['target_section_id']) if value.get('target_section_id') else None
        items.append(PromotionItem(tenant=access.tenant,branch=batch.branch,batch=batch,enrollment=e,target_class=klass,target_section=section,outcome=value.get('outcome','promote')))
    batch.fingerprint=inspect(batch,items,access);persist(batch,access,'promotion_previewed')
    for item in items:persist(item,access,'promotion_item_previewed')
    return batch


@transaction.atomic
def commit(pk,data,*,access):
    access.require('promotion','commit');lock(access);batch=get(access,PromotionBatch,pk)
    if data.get('fingerprint')!=batch.fingerprint:invalid('fingerprint','Confirm the saved preview before committing.')
    if batch.status=='committed':return batch
    items=list(batch.items.select_related('enrollment__student').order_by('created_at','pk'))
    if inspect(batch,items,access)!=batch.fingerprint:invalid('preview','Placement, results or capacity changed. Create a fresh preview.')
    for item in items:
        previous=item.enrollment;student=previous.student
        previous.status={'promote':'promoted','repeat':'repeated','graduate':'graduated'}[item.outcome]
        previous.end_date=batch.effective_date-timedelta(days=1)
        persist(previous,access,'enrollment_'+previous.status)
        next_row=None
        if item.outcome=='graduate':student.status='graduated';persist(student,access,'student_graduated')
        else:
            next_row=placement(student,{'branch_id':str(batch.branch_id),'academic_year_id':str(batch.target_year_id),'school_class_id':str(item.target_class_id),'section_id':str(item.target_section_id) if item.target_section_id else None,'start_date':str(batch.effective_date)},access,kind='promotion' if item.outcome=='promote' else 'repetition',previous=previous)
            item.result_enrollment=next_row;persist(item,access,'promotion_item_committed')
        persist(StudentTransition(tenant=access.tenant,branch=batch.branch,student=student,from_enrollment=previous,to_enrollment=next_row,outcome=previous.status,effective_date=batch.effective_date,reason=batch.reason,requested_by=batch.created_by,approved_by=access.user),access,'promotion_transition')
    batch.status='committed';return persist(batch,access,'promotion_committed')
