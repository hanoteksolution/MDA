"""Provision local shop users from cloud credentials (first desktop login)."""

from __future__ import annotations

import json
from urllib import error, request

from django.db import transaction

from apps.authentication.models import Role, User
from apps.authentication.services.auth_service import AuthService
from apps.inventory.models import Warehouse
from apps.platform.models import Tenant
from apps.platform.services.sync_service import ShopSyncService
from apps.settings_app.models import Branch, Company


def _http_get_json(url: str, headers: dict) -> dict:
    req = request.Request(url, headers=headers, method="GET")
    try:
        with request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise ValueError(f"Cloud verification failed ({exc.code}): {detail}") from exc
    except error.URLError as exc:
        raise ValueError(f"Cloud server unreachable: {exc.reason}") from exc
    return body.get("data", body)


class DesktopProvisionService:
    @staticmethod
    def user_status(*, username: str) -> dict:
        user = User.objects.filter(username__iexact=username.strip(), deleted_at__isnull=True).first()
        if not user:
            return {"exists": False, "provisioned": False}
        flag = ShopSyncService._get_setting(f"sync.provisioned.{user.username.lower()}", "")
        return {"exists": True, "provisioned": flag == "1"}

    @staticmethod
    def _fetch_cloud_profile(*, cloud_base: str, access_token: str) -> dict:
        cloud = cloud_base.rstrip("/")
        return _http_get_json(
            f"{cloud}/auth/me/",
            {"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )

    @staticmethod
    def _ensure_shop_context(*, slug: str, sync_secret: str, shop_name: str = "") -> tuple[Tenant, Company, Branch]:
        company = Company.active_objects().first()
        if not company:
            company = Company.objects.create(name=shop_name or slug)

        tenant = Tenant.objects.filter(slug=slug).first()
        if not tenant:
            tenant = Tenant.objects.create(
                name=shop_name or company.name or slug,
                slug=slug,
                sync_secret=sync_secret,
                is_active=True,
            )
        elif sync_secret and tenant.sync_secret != sync_secret:
            tenant.sync_secret = sync_secret
            tenant.save(update_fields=["sync_secret", "updated_at"])

        if company.tenant_id != tenant.id:
            company.tenant = tenant
            company.save(update_fields=["tenant", "updated_at"])

        branch = (
            Branch.active_objects()
            .filter(company=company, is_default=True)
            .first()
        )
        if not branch:
            branch = Branch.active_objects().filter(company=company).first()
        if not branch:
            branch = Branch.objects.create(
                company=company,
                name="Main Branch",
                code="BR01",
                is_default=True,
                is_active=True,
            )

        if not Warehouse.active_objects().filter(branch=branch).exists():
            Warehouse.objects.create(
                branch=branch,
                code="WH01",
                name="Main Warehouse",
                is_default=True,
                is_active=True,
            )

        return tenant, company, branch

    @staticmethod
    @transaction.atomic
    def provision_from_cloud(
        *,
        username: str,
        password: str,
        cloud_access_token: str,
        request=None,
    ) -> tuple[User, dict]:
        username = username.strip()
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")

        cfg = ShopSyncService.get_config()
        cloud = (cfg.get("cloud_api_base") or "").rstrip("/")
        slug = (cfg.get("tenant_slug") or "").strip()
        secret = (cfg.get("sync_secret") or "").strip()
        if not cloud or not slug or not secret:
            raise ValueError(
                "Shop connection is not configured. Open Settings → Connection and save cloud URL, shop slug, and sync secret."
            )

        profile = DesktopProvisionService._fetch_cloud_profile(
            cloud_base=cloud,
            access_token=cloud_access_token,
        )
        if profile.get("username", "").lower() != username.lower():
            raise ValueError("Cloud account does not match the username entered.")

        if profile.get("is_platform_admin"):
            raise ValueError("Platform admin accounts cannot use shop provisioning. Sign in locally.")

        cloud_slug = profile.get("shop_slug") or ""
        if cloud_slug and cloud_slug != slug:
            raise ValueError("This account belongs to a different shop.")

        role_data = profile.get("role") or {}
        role_slug = role_data.get("slug")
        if not role_slug:
            raise ValueError("Cloud account has no role assigned. Ask your platform admin to set a role.")
        role = Role.objects.filter(slug=role_slug, deleted_at__isnull=True).first()
        if not role:
            raise ValueError(f"Role '{role_slug}' is not available on this device. Run system bootstrap.")

        tenant, company, branch = DesktopProvisionService._ensure_shop_context(
            slug=slug,
            sync_secret=secret,
            shop_name=Company.active_objects().values_list("name", flat=True).first() or slug,
        )

        user = User.objects.filter(username__iexact=username, deleted_at__isnull=True).first()
        fields = {
            "email": profile.get("email") or "",
            "first_name": profile.get("first_name") or "",
            "last_name": profile.get("last_name") or "",
            "phone": profile.get("phone") or "",
            "role": role,
            "branch": branch,
            "tenant": tenant,
            "is_active": True,
            "is_platform_admin": False,
            "is_staff": False,
            "is_superuser": False,
        }
        if user:
            for key, value in fields.items():
                setattr(user, key, value)
            user.set_password(password)
            user.save()
        else:
            user = User.objects.create_user(username=username, password=password, **fields)

        ShopSyncService._set_setting(f"sync.provisioned.{user.username.lower()}", "1", user=user)
        ShopSyncService._set_setting("sync.initial_pull_done", "0", user=user)

        _, tokens = AuthService.login(username=username, password=password, request=request)
        if not tokens:
            raise ValueError("Local session could not be created after provisioning.")

        return user, tokens
