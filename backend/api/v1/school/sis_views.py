"""Thin authenticated SIS resource and workflow endpoints."""
from django.http import FileResponse, HttpResponse
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework import serializers
from apps.school.repositories.sis import MODELS, StudentAccess, queryset
from apps.school.repositories.sis_filters import filters
from apps.school.sis_permissions import RESOURCES, SIS_PERMISSIONS
from apps.school.serializers.sis import serialize
from apps.school.services.sis_crud import StudentCrudService
from apps.school.services import admission_workflow, student_creation, student_lifecycle, document_service, private_files
from apps.school.services.enrollment_service import EnrollmentService
from apps.school.services.attendance_service import AttendanceService, roster_view
from apps.school.services.timetable_service import TimetableService
from core.responses.api_response import success_response
from .views import SchoolView, page


class SisView(SchoolView):
    def access(self,request):return StudentAccess(user=request.user,request=request)


class SisResourceView(SisView):
    def get(self,request,resource,pk=None):
        if resource not in MODELS:raise NotFound()
        access=self.access(request);access.require(RESOURCES[resource],'view')
        from apps.school.fee_contracts import MODELS as FEES
        if resource in FEES:
            from apps.sales.services.billing_service import require
            require(access,write=False)
            if resource=='billing-customers' and not access.user.has_permission('customers.view'):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied('customers.view permission is required.')
        qs=queryset(resource,access,archived=request.query_params.get('archived')=='true')
        if pk:
            row=qs.filter(pk=pk).first()
            if not row:raise NotFound()
            return success_response(data=serialize(row))
        return page(request,filters(qs,request.query_params),serialize)

    def post(self,request,resource,pk=None,action=None):
        if resource not in MODELS:raise NotFound()
        access=self.access(request);data=request.data
        if not isinstance(data,dict):raise ValidationError({'detail':'Expected a JSON object.'})
        from apps.school.fee_contracts import MODELS as FEES
        if resource in FEES:
            from apps.school.services.fee_commands import command
            row=command(resource,pk,action,data,access)
            return success_response(data=serialize(row),status=200 if pk else 201)
        from apps.school.services import marks_service, promotion_service
        if resource=='academic-assessments' and action=='marks':row=marks_service.save_marks(pk,data,access=access)
        elif resource=='exams' and action:row=marks_service.exam_action(pk,action,data,access=access)
        elif resource in ('assignments','submissions') and action:row=marks_service.assignment_action(resource,pk,action,data,access=access)
        elif resource=='promotion-batches' and action=='commit':row=promotion_service.commit(pk,data,access=access)
        elif resource=='promotion-batches' and not pk:row=promotion_service.preview(data,access=access)
        elif action in ('archive','restore'):
            row=StudentCrudService.archive(resource,pk,access=access,restore=action=='restore')
        elif resource=='timetable-versions' and action in ('publish','clone'):
            row=(TimetableService.publish if action=='publish' else TimetableService.clone)(pk,data,access=access)
        elif resource=='attendance-sessions' and not pk and not action:row=AttendanceService.take(data,access=access)
        elif resource=='attendance-sessions' and action=='submit':row=AttendanceService.submit(pk,access=access)
        elif resource=='attendance-records' and action=='correct':row=AttendanceService.request_correction(pk,data,access=access)
        elif resource=='attendance-corrections' and action in ('approve','reject'):row=AttendanceService.decide(pk,action=='approve',data,access=access)
        elif resource=='applications' and action:
            if action=='decide':row=admission_workflow.decide(pk,data,access=access)
            elif action=='enroll':row=student_creation.convert(pk,data,access=access)
            else:row=admission_workflow.transition(pk,action,data,access=access)
        elif resource=='students' and action:
            row=student_lifecycle.alumni(pk,data,access=access) if action=='alumni' else student_lifecycle.transition(pk,action,data,access=access)
        elif resource in ('assessments','interviews') and action:row=admission_workflow.appointment(resource,pk,action,data,access=access)
        elif resource in ('applicant-documents','student-documents') and action=='verify':row=document_service.verify(resource,pk,data,access=access)
        elif action:raise NotFound()
        elif resource=='students':row=student_creation.direct(data,access=access)
        elif resource=='enrollments':row=EnrollmentService.create(data.get('student_id'),data,access=access)
        else:row=StudentCrudService.save(resource,data,access=access)
        return success_response(data=serialize(row),status=200 if pk else 201)

    def patch(self,request,resource,pk):
        if resource not in MODELS:raise NotFound()
        if not isinstance(request.data,dict):raise ValidationError({'detail':'Expected a JSON object.'})
        access=self.access(request)
        row=EnrollmentService.update(pk,request.data,access=access) if resource=='enrollments' else StudentCrudService.save(resource,request.data,pk=pk,access=access)
        return success_response(data=serialize(row))

    def delete(self,request,resource,pk):
        if resource not in MODELS:raise NotFound()
        return success_response(data=serialize(StudentCrudService.archive(resource,pk,access=self.access(request))))


class SisCapabilitiesView(SisView):
    def get(self,request):
        access=self.access(request)
        return success_response(data=[code for code,_,_ in SIS_PERMISSIONS if access.allows(code.split('.')[1],code.split('.')[2])])


class SisFileView(SisView):
    def post(self,request):
        access=self.access(request)
        branch=serializers.UUIDField().run_validation(request.query_params.get('branch_id'))
        row=private_files.upload(request.FILES.get('file'),branch,access=access,purpose=request.query_params.get('purpose'))
        return success_response(data=serialize(row),status=201)

    def get(self,request,pk):
        row,path=private_files.download(pk,access=self.access(request))
        response=FileResponse(path.open('rb'),as_attachment=request.query_params.get('download')=='true',filename=row.original_name,content_type=row.content_type)
        response['Cache-Control']='private, no-store';response['X-Content-Type-Options']='nosniff'
        response['Content-Security-Policy']="sandbox; default-src 'none'"
        return response


class SisExportView(SisView):
    def get(self,request,resource):
        if resource not in ('students','applicants','guardians','families','enrollments'):raise NotFound()
        import csv,io
        access=self.access(request);access.require(RESOURCES[resource],'export');access.require(RESOURCES[resource],'view')
        qs=filters(queryset(resource,access),request.query_params)
        if qs.count()>10000:raise ValidationError({'filters':'Narrow the export to at most 10,000 records.'})
        columns={'students':['number','first_name','last_name','branch_name','current_class','current_section','status','admission_date'], 'applicants':['number','first_name','last_name','branch_name','status','previous_school'], 'guardians':['number','first_name','last_name','phone','email','status'], 'families':['code','name','phone','email','student_count','status'], 'enrollments':['student_name','academic_year_name','branch_name','school_class_name','section_name','roll_number','start_date','end_date','status']}[resource]
        output=io.StringIO();writer=csv.writer(output);writer.writerow(columns)
        for row in qs.iterator(chunk_size=500):
            data=serialize(row);values=[str(data.get(c) or '') for c in columns]
            writer.writerow(["'"+v if v.lstrip().startswith(('=','+','-','@','\t','\r')) else v for v in values])
        response=HttpResponse(output.getvalue(),content_type='text/csv');response['Content-Disposition']=f'attachment; filename="school-{resource}.csv"';response['Cache-Control']='no-store'
        return response


class SisDuplicatesView(SisView):
    def post(self,request):
        access=self.access(request);access.require('student','view')
        data=dict(request.data)
        if data.get('date_of_birth'):data['date_of_birth']=serializers.DateField().run_validation(data['date_of_birth'])
        return success_response(data=[{'id':str(row.pk),'number':row.number,'name':str(row),'date_of_birth':row.date_of_birth.isoformat()} for row in student_creation.duplicate_candidates(data,access)])


class AttendanceRosterView(SisView):
    def get(self,request):
        return success_response(data=roster_view(self.access(request),request.query_params))
