"""Shared financial action permissions and School configuration dispatch."""
from rest_framework.exceptions import NotFound
from apps.sales.services import billing_service as billing
from apps.settings_app.models import Branch
from .fee_crud import FeeCrud,finance_settings
from . import fee_generation


def command(resource,pk,action,data,access):
    if resource=='fee-batches':
        return fee_generation.issue(pk,data,access=access) if action=='issue' else fee_generation.preview(data,access=access) if not pk else unknown()
    if resource in ('fee-structures','fee-discounts') and action:return FeeCrud.action(resource,pk,action,data,access=access)
    if resource=='billing-receipts':
        if not pk:
            access.require('billing_receipt','collect');branch=billing.get(access,Branch,data.get('branch_id'))
            return billing.collect(data,access=access,settings=finance_settings(access,branch))
        if action=='reverse':access.require('billing_receipt','reverse');return billing.reverse_receipt(pk,data,access=access)
    if resource=='billing-allocations':
        if not pk:access.require('billing_allocation','allocate');return billing.allocate(data,access=access)
        if action=='reverse':access.require('billing_allocation','reverse');return billing.reverse_allocation(pk,data,access=access)
    if resource in ('billing-credits','billing-refunds') and action=='reverse':
        from apps.sales.models.billing import BillingCredit,BillingRefund
        access.require('billing_credit' if resource=='billing-credits' else 'billing_refund','reverse')
        return billing.reverse_adjustment(BillingCredit if resource=='billing-credits' else BillingRefund,pk,data,access=access)
    if resource=='billing-credits' and not pk:access.require('billing_credit','issue');return billing.credit(data,access=access)
    if resource=='billing-refunds' and not pk:access.require('billing_refund','issue');return billing.refund(data,access=access)
    if action:unknown()
    return FeeCrud.save(resource,data,access=access,pk=pk)

def unknown():raise NotFound('Unknown financial command.')
