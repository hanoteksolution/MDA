from apps.audit.models.audit_log import AuditLog


class AuditRepository:
    @staticmethod
    def create(*, user=None, action, module, entity_type="", entity_id=None, old_values=None, new_values=None, request=None):
        ip_address = None
        user_agent = ""
        if request:
            ip_address = request.META.get("REMOTE_ADDR")
            user_agent = request.META.get("HTTP_USER_AGENT", "")

        return AuditLog.objects.create(
            user=user,
            action=action,
            module=module,
            entity_type=entity_type,
            entity_id=entity_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    def list_logs(*, user=None, action=None, module=None, date_from=None, date_to=None):
        qs = AuditLog.objects.select_related("user").all()
        if user:
            qs = qs.filter(user_id=user)
        if action:
            qs = qs.filter(action=action)
        if module:
            qs = qs.filter(module=module)
        if date_from:
            qs = qs.filter(timestamp__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__lte=date_to)
        return qs
