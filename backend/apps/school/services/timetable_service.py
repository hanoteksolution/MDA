"""Timetable lifecycle: publish (atomic replace, full re-check) and clone-to-draft."""
from django.db import transaction
from django.utils import timezone
from apps.school.models import TimetableVersion, TimetableEntry
from apps.school.serializers.sis import serialize
from .sis_common import get, invalid, lock, persist, reason, date_value
from .ops_integrity import entry_conflict, window_overlaps, overlaps


def _live(version):
    return TimetableEntry.objects.filter(version=version, status='active', deleted_at__isnull=True).select_related('period', 'staff', 'version')


class TimetableService:
    @staticmethod
    @transaction.atomic
    def publish(pk, data, *, access):
        access.require('timetable', 'publish'); lock(access)
        version = get(access, TimetableVersion, pk)
        if version.status != 'draft':
            invalid('status', 'Only a draft timetable can be published.')
        if version.academic_year.status not in ('planning', 'active'):
            invalid('academic_year_id', 'The academic year is closed.')
        entries = list(_live(version))
        if not entries:
            invalid('status', 'Add at least one lesson before publishing.')
        for index, entry in enumerate(entries):
            for other in entries[index + 1:]:
                message = entry_conflict(entry, other)
                if message:
                    invalid('status', f'Cannot publish: {message} ({entry.school_class} / {entry.period}).')
            if entry.staff_id and (not entry.staff.status == 'active'):
                invalid('status', 'Cannot publish: a scheduled teacher is no longer active.')
            if entry.staff_id:
                others = TimetableEntry.objects.filter(tenant=version.tenant, status='active', deleted_at__isnull=True, weekday=entry.weekday, staff__employee_id=entry.staff.employee_id, version__status='published', version__deleted_at__isnull=True).exclude(version__branch_id=version.branch_id).select_related('period', 'version')
                for other in others:
                    if window_overlaps(version.effective_from, version.effective_to, other.version.effective_from, other.version.effective_to) and overlaps(entry.period.start_time, entry.period.end_time, other.period.start_time, other.period.end_time):
                        invalid('status', 'Cannot publish: a teacher is scheduled at another campus in an overlapping period.')
        for live in TimetableVersion.objects.filter(tenant=version.tenant, branch=version.branch, academic_year=version.academic_year, status='published', deleted_at__isnull=True):
            before = serialize(live, audit=True)
            live.status = 'archived'
            persist(live, access, 'timetable_superseded', before)
        before = serialize(version, audit=True)
        version.status, version.published_at, version.published_by = 'published', timezone.now(), access.user
        return persist(version, access, 'timetable_published', before)

    @staticmethod
    @transaction.atomic
    def clone(pk, data, *, access):
        access.require('timetable', 'create'); lock(access)
        source = get(access, TimetableVersion, pk)
        name = str(data.get('name', '')).strip()
        if not name:
            invalid('name', 'Name the new draft.')
        clone = TimetableVersion(tenant=source.tenant, branch=source.branch, academic_year=source.academic_year, name=name, status='draft',
                                 effective_from=date_value(data, 'effective_from', source.effective_from.isoformat()), effective_to=source.effective_to)
        from .ops_integrity import validate_ops
        validate_ops(clone, access)
        persist(clone, access, 'timetable_cloned')
        for entry in _live(source):
            entry.pk = None
            entry._state.adding = True
            entry.version = clone
            entry.created_by = access.user
            entry.save()
        return clone
