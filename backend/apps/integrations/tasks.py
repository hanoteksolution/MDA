from celery import shared_task

from apps.integrations.services.sms_service import SmsService


@shared_task(name="integrations.dispatch_sms")
def dispatch_sms(log_id):
    log = SmsService.dispatch_safe(log_id)
    return {"status": log.status if log else "error"}


@shared_task(name="integrations.retry_due_sms")
def retry_due_sms():
    return {"retried": SmsService.retry_due()}


@shared_task(name="integrations.expire_payment_intents")
def expire_payment_intents():
    from apps.integrations.services.payment_service import PaymentService

    from apps.platform.services.subscription_billing_service import SubscriptionBillingService

    return {"expired": PaymentService.expire_due(), "subscription_checkouts": SubscriptionBillingService.expire_stale()}


@shared_task(name="integrations.expire_sms_credits")
def expire_sms_credits():
    from apps.integrations.services.sms_credit_service import SmsCreditService, SmsPurchaseService

    return {"expired_units": SmsCreditService.expire_due(), "stale_purchases": SmsPurchaseService.expire_stale()}
