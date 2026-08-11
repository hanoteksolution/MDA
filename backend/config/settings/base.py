from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = config("SECRET_KEY", default="dev-secret-key-change-in-production")

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "core",
    "apps.authentication",
    "apps.settings_app",
    "apps.audit",
    "apps.products",
    "apps.inventory",
    "apps.customers",
    "apps.suppliers",
    "apps.purchases",
    "apps.sales",
    "apps.platform",
    "apps.futsal",
    "apps.pharmacy",
    "apps.gym",
    "apps.restaurant",
    "apps.hotel",
    "apps.property_management",
    "apps.housing_rental",
    "apps.office_rental",
    "apps.project_management",
    "apps.travel_agency",
    "apps.finance",
    "apps.reports",
    "apps.notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "core.middleware.security_headers.SecurityHeadersMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.platform.middleware.TenantResolutionMiddleware",
    "apps.platform.middleware_modules.ModuleGateMiddleware",
    "apps.platform.middleware_subscription.SubscriptionEntitlementMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

AUTH_USER_MODEL = "authentication.User"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME", default="mda_erp"),
        "USER": config("DB_USER", default="postgres"),
        "PASSWORD": config("DB_PASSWORD", default="postgres"),
        "HOST": config("DB_HOST", default="localhost"),
        "PORT": config("DB_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "core.authentication.TenantAwareJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "EXCEPTION_HANDLER": "core.exceptions.custom_exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/minute",
        "user": "600/minute",
        "auth": "20/minute",
    },
}

from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default=(
        "http://localhost:5173,"
        "http://127.0.0.1:5173,"
        "https://tauri.localhost,"
        "http://tauri.localhost"
    ),
).split(",")

CORS_ALLOW_CREDENTIALS = True

# SaaS subdomain base: {slug}.erp.safaritechno.com
TENANT_BASE_DOMAIN = config("TENANT_BASE_DOMAIN", default="erp.safaritechno.com")

# Apex / platform hosts that do not bind a shop tenant
PLATFORM_HOSTS = config("PLATFORM_HOSTS", default="")

# When True, JWT users on a tenant host must belong to that tenant
TENANT_HOST_ENFORCEMENT = config("TENANT_HOST_ENFORCEMENT", default=True, cast=bool)

REDIS_URL = config("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = config("CELERY_TASK_ALWAYS_EAGER", default=False, cast=bool)
CELERY_TASK_EAGER_PROPAGATES = config("CELERY_TASK_EAGER_PROPAGATES", default=True, cast=bool)

# Central Accounting Engine
ACCOUNTING_ENGINE_ENABLED = config("ACCOUNTING_ENGINE_ENABLED", default=True, cast=bool)
ACCOUNTING_STRICT_AFTER_CUTOVER = config(
    "ACCOUNTING_STRICT_AFTER_CUTOVER", default=True, cast=bool
)

CELERY_BEAT_SCHEDULE = {
    "notifications-daily-scans": {
        "task": "notifications.run_all_scheduled_scans",
        "schedule": 60 * 60 * 6,
    },
    "finance-accounting-health": {
        "task": "finance.scan_accounting_health",
        "schedule": 60 * 60 * 24,
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "MDA ERP API",
    "DESCRIPTION": "Multi-tenant ERP REST API for web and mobile clients.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
            }
        }
    },
    "SECURITY": [{"BearerAuth": []}],
}

# Mobile clients may send this header on platform API hosts (e.g. api.{base_domain}).
MOBILE_TENANT_SLUG_HEADER = "X-Tenant-Slug"

# Login lockout (STEP 30)
LOGIN_LOCKOUT_MAX_ATTEMPTS = config("LOGIN_LOCKOUT_MAX_ATTEMPTS", default=5, cast=int)
LOGIN_LOCKOUT_WINDOW_MINUTES = config("LOGIN_LOCKOUT_WINDOW_MINUTES", default=15, cast=int)
LOGIN_LOCKOUT_DURATION_MINUTES = config("LOGIN_LOCKOUT_DURATION_MINUTES", default=30, cast=int)

SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
