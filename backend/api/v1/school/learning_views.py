"""Academic read endpoints using the same server-side scope as commands."""
from django.http import HttpResponse
from django.utils.html import escape
from apps.school.models.learning import ReportCardVersion
from apps.school.services.sis_common import get
from apps.school.services.marks_service import roster_view
from core.responses.api_response import success_response
from .sis_views import SisView


class MarksRosterView(SisView):
    def get(self,request,pk):return success_response(data=roster_view(pk,self.access(request)))


class ReportPrintView(SisView):
    def get(self,request,pk):
        access=self.access(request);access.require('report_card','view')
        row=get(access,ReportCardVersion,pk);data=row.data
        rows=''.join(f'<tr><td>{escape(s["name"])}</td><td>{escape(s["percentage"] or "Exempt")}</td><td>{escape(s["grade"])}</td></tr>' for s in data['subjects'].values())
        response=HttpResponse(f'<!doctype html><html lang="en"><meta charset="utf-8"><title>Report card</title><body><h1>{escape(data["name"])}</h1><p>{escape(data["exam"])} · {escape(data["academic_year"])} · Version {data["version"]}</p><table><thead><tr><th>Subject</th><th>Percentage</th><th>Grade</th></tr></thead><tbody>{rows}</tbody></table><p>Overall: {escape(data["percentage"] or "Exempt")}</p><p>Daily attendance: {escape(str(data["attendance"]))}</p></body></html>',content_type='text/html')
        response['Cache-Control']='private, no-store';response['Content-Security-Policy']="default-src 'none'";response['X-Content-Type-Options']='nosniff'
        return response
