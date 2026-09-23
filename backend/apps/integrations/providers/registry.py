"""Provider registries. Only the mock (and, for SMS, the generic HTTP adapter) exist (decision D7)."""

from apps.integrations.providers.custom_http import CustomHttpProvider
from apps.integrations.providers.mock import MockProvider
from apps.integrations.providers.payment_mock import MockPaymentProvider

PROVIDER_REGISTRY = {
    MockProvider.type_code: MockProvider,
    CustomHttpProvider.type_code: CustomHttpProvider,
}

PAYMENT_PROVIDER_REGISTRY = {MockPaymentProvider.type_code: MockPaymentProvider}


def get_adapter_class(provider_type: str):
    try:
        return PROVIDER_REGISTRY[provider_type]
    except KeyError:
        raise LookupError(f"Unknown SMS provider type: {provider_type!r}")


def get_payment_adapter_class(provider_type: str):
    try:
        return PAYMENT_PROVIDER_REGISTRY[provider_type]
    except KeyError:
        raise LookupError(f"Unknown payment provider type: {provider_type!r}")
