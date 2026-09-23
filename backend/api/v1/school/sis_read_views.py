"""Scoped dashboard, activity and form metadata."""
from django.db.models import Q, Count
from django.utils import timezone
from rest_framework.exceptions import NotFound
from apps.school.models import AdmissionApplication, AdmissionInterview, AdmissionAssessment, Student
from apps.school.repositories.sis import MODELS, queryset
from apps.school.repositories.sis_filters import filters, missing_annotation
from apps.school.serializers.sis import serialize, FIELDS
from apps.school.sis_permissions import RESOURCES
from core.responses.api_response import success_response
from .sis_views import SisView
from .views import page


class SisDashboardView(SisView):
    def get(self,request):
        access=self.access(request);access.require('admission','view')
        apps=filters(queryset('applications',access),request.query_params)
        counts=dict(apps.order_by().values_list('status').annotate(count=Count('pk')))
        total=sum(counts.values());enrolled=counts.get('enrolled',0)
        data={'total_applications':total,'new_applications':counts.get('draft',0)+counts.get('submitted',0),'under_review':counts.get('under_review',0),'pending_documents':apps.filter(missing_documents=True).count(),'accepted':counts.get('accepted',0),'waitlisted':counts.get('waitlisted',0),'rejected':counts.get('rejected',0),'enrolled':enrolled,'conversion_rate':round(100*enrolled/total,1) if total else 0}
        for resource,label in (('assessments','assessment_scheduled'),('interviews','interview_scheduled')):
            data[label]=queryset(resource,access).filter(application_id__in=apps.values('pk'),status='scheduled').count() if access.allows(RESOURCES[resource],'view') else None
        for field,label in (('school_class__name','by_class'),('branch__name','by_campus'),('applicant__source','by_source')):
            data[label]=list(apps.order_by().values(field).annotate(count=Count('pk')).order_by('-count')[:20])
        data['recent_applications']=[serialize(row) for row in apps.order_by('-created_at')[:8]]
        data['missing_documents']=[serialize(row) for row in apps.filter(missing_documents=True)[:8]]
        data['upcoming_interviews']=[serialize(row) for row in queryset('interviews',access).filter(application_id__in=apps.values('pk'),status='scheduled',date__gte=timezone.localdate()).order_by('date','start_time')[:8]] if access.allows('interview','view') else []
        return success_response(data=data)


class SisActivityView(SisView):
    def get(self,request,resource,pk):
        if resource not in MODELS:raise NotFound()
        access=self.access(request);access.require(RESOURCES[resource],'view')
        row=queryset(resource,access,archived=request.query_params.get('archived')=='true').filter(pk=pk).first()
        if not row:raise NotFound()
        audit=request.query_params.get('audit')=='true'
        if audit and resource=='students':access.require('student','audit')
        from apps.audit.models import AuditLog
        entities=Q(entity_id=pk)
        if resource in ('students','applications','applicants'):
            for child,model in MODELS.items():
                field={'students':'student_id','applications':'application_id','applicants':'applicant_id'}[resource]
                if child!=resource and field in {f.attname for f in model._meta.fields} and access.allows(RESOURCES[child],'view'):
                    entities|=Q(entity_id__in=queryset(child,access).filter(**{field:pk}).values('pk'))
        logs=AuditLog.objects.filter(tenant=access.tenant,module='school').filter(entities).select_related('user').order_by('-timestamp','pk')
        def summary(log):
            data={'id':str(log.pk),'action':log.action,'timestamp':log.timestamp.isoformat(),'actor':log.user.get_full_name() or log.user.username if log.user else 'System','entity_id':str(log.entity_id),'description':log.action.replace('_',' ').capitalize()}
            if audit:data.update(before=log.old_values,after=log.new_values)
            return data
        return page(request,logs,summary)


class SisSchemaView(SisView):
    def get(self,request,resource):
        if resource not in MODELS:raise NotFound()
        access=self.access(request)
        if not any(access.allows(RESOURCES[resource],a) for a in ('view','create','update')):access.require(RESOURCES[resource],'view')
        model=MODELS[resource]
        related={v:k for k,v in MODELS.items()}
        from apps.school.repositories.foundation import MODELS as FOUNDATION
        related.update({v:k for k,v in FOUNDATION.items()})
        fields=[]
        names=FIELDS[resource].split()
        if resource=='students':names+=['branch_id','admission_date']
        for name in names:
            field=model._meta.get_field(name)
            kind='text';lookup=None
            if field.is_relation:
                kind='relation';lookup=related.get(field.related_model)
                if field.related_model._meta.app_label=='authentication':lookup='users' if name=='user_id' else 'admissions-staff'
                if field.related_model._meta.model_name=='schoolfile':kind='file'
            elif field.choices:kind='select'
            elif field.get_internal_type()=='BooleanField':kind='checkbox'
            elif field.get_internal_type()=='DateField':kind='date'
            elif field.get_internal_type()=='TimeField':kind='time'
            elif 'Integer' in field.get_internal_type() or field.get_internal_type()=='DecimalField':kind='number'
            elif field.get_internal_type()=='TextField':kind='textarea'
            elif field.get_internal_type()=='JSONField':kind='multiselect'
            elif field.get_internal_type()=='EmailField':kind='email'
            default=field.get_default() if field.has_default() else ''
            if hasattr(default,'isoformat'):default=default.isoformat()
            fields.append({'name':name,'label':str(field.verbose_name).replace('_',' ').capitalize(),'kind':kind,'lookup':lookup,'sis':lookup in MODELS,'required':not(field.blank or field.null or field.has_default()),'nullable':field.null,'choices':[{'value':v,'label':label} for v,label in field.choices] if field.choices else [],'default':default,'max_length':field.max_length})
        return success_response(data=fields)


class SisStaffView(SisView):
    def get(self,request):
        from apps.authentication.models import User
        from apps.school.repositories.sis import StudentAccess
        from rest_framework import serializers
        access=self.access(request);access.require('admission','view')
        branch=access.campus(serializers.UUIDField().run_validation(request.query_params.get('branch_id')))
        action=request.query_params.get('action','review')
        if action not in ('review','assess','interview'):raise NotFound()
        ids=[]
        for person in User.objects.filter(tenant=access.tenant,is_active=True,deleted_at__isnull=True):
            if person.has_permission('school.admission.'+action) and StudentAccess(user=person).campuses().filter(pk=branch.pk).exists():ids.append(person.pk)
        return page(request,User.objects.filter(pk__in=ids).order_by('username'),lambda person:{'id':str(person.pk),'name':person.get_full_name() or person.username})
