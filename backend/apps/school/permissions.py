"""Foundation permission catalog and narrow compatibility aliases."""
RESOURCES = {
    "campuses": "campus", "academic-years": "academic_year", "terms": "term",
    "levels": "level", "classes": "class", "sections": "section", "shifts": "shift",
    "subjects": "subject", "subject-categories": "subject_category",
    "subject-offerings": "subject_offering", "campus-access": "campus_access",
}
ACTIONS = ("view", "create", "update", "archive", "restore")
FOUNDATION_PERMISSIONS = [
    (f"school.{resource}.{action}", f"School {resource.replace('_', ' ')}: {action}", "school")
    for resource in RESOURCES.values() for action in ACTIONS
] + [(f"school.{r}.{a}", f"School {r}: {a}", "school") for r in ("academic_year", "term") for a in ("activate", "close")]
FOUNDATION_PERMISSIONS += [(f"school.{code}", label, "school") for code, label in (
    ("profile.view", "View school profile"), ("profile.update", "Update school profile"),
    ("campus.all", "Access all school campuses"), ("teacher.assignable", "Eligible school teacher"),
    ("leadership.assignable", "Eligible school principal"),
)]


def allowed(user, resource, action, *, codes=None, revoked=None):
    code = f"school.{resource}.{action}"
    if not user or not user.is_authenticated or not user.is_active or user.deleted_at:
        return False
    if user.is_elevated_admin:
        return True
    # Explicit revocation wins over legacy compatibility grants.
    revoked = set(user.get_revoked_permissions()) if revoked is None else revoked
    codes = set(user.get_permissions()) if codes is None else codes
    if code in revoked:
        return False
    if code in codes:
        return True
    aliases = []
    if resource == "profile":
        aliases = [f"school.settings.{action}"]
    elif resource in ("academic_year", "term") and action in ("view", "create", "update", "archive", "activate"):
        aliases = [f"school.academic.{action}"]
    return any(c in codes for c in aliases)
