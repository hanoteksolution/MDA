"""Phase 6 command/read adapters; all monetary decisions remain on the server."""
from django.http import HttpResponse
from django.utils.html import escape
from core.responses.api_response import success_response
from apps.school.services.fee_reads import summary
from apps.sales.services import billing_service as billing
from apps.sales.models.billing import BillingReceipt
from .sis_views import SisView

class FeeSummaryView(SisView):
    def get(self,request):return success_response(data=summary(self.access(request),request.query_params))

class BillingReceiptPrintView(SisView):
    def get(self,request,pk):
        access=self.access(request);access.require('billing_receipt','view');billing.require(access,write=False);row=billing.get(access,BillingReceipt,pk)
        response=HttpResponse(f'<!doctype html><html lang="en"><meta charset="utf-8"><title>Receipt</title><body><h1>{escape(str(row))}</h1><p>{escape(row.customer.full_name)}</p><p>Date: {row.received_date}</p><p>Amount: {escape(access.tenant.currency)} {row.amount}</p><p>Method: {escape(row.method.name)}</p><p>Reference: {escape(row.reference)}</p><p>Status: {escape(row.status)}</p><p>Available advance: {billing.available(row)}</p></body></html>',content_type='text/html')
        response['Cache-Control']='private, no-store';response['Content-Security-Policy']="default-src 'none'";return response
