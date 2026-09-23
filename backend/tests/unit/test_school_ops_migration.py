"""Phase 4 additive migration keeps Phase 3 data and reverses when empty."""
import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
def test_phase4_upgrade_preserves_sis_and_reverses_empty():
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    previous = [('school', '0005_admissionapplication_admissiondecision_and_more')]
    try:
        executor.migrate(previous)
        apps = executor.loader.project_state(previous).apps
        tenant = apps.get_model('platform', 'Tenant').objects.create(name='Phase 4 migration', slug='phase4-migration')
        company = apps.get_model('settings_app', 'Company').objects.create(tenant_id=tenant.pk, name='School')
        branch = apps.get_model('settings_app', 'Branch').objects.create(tenant_id=tenant.pk, company_id=company.pk, name='Campus', code='P4')
        student = apps.get_model('school', 'Student').objects.create(tenant_id=tenant.pk, branch_id=branch.pk, first_name='Keep', date_of_birth='2015-01-01', number='S-1', admission_date='2026-01-01')
        MigrationExecutor(connection).migrate(latest)
        from apps.school.models import Student, AttendanceSession, TimetableEntry
        assert Student.objects.get(pk=student.pk).first_name == 'Keep'
        assert not AttendanceSession.objects.exists() and not TimetableEntry.objects.exists()
        MigrationExecutor(connection).migrate(previous)
        old = MigrationExecutor(connection).loader.project_state(previous).apps
        assert old.get_model('school', 'Student').objects.filter(pk=student.pk).exists()
    finally:
        MigrationExecutor(connection).migrate(latest)
