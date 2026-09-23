"""The Phase 3 additive migration preserves the verified Phase 2 calendar."""
import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

@pytest.mark.django_db(transaction=True)
def test_phase3_upgrade_preserves_foundation():
    executor=MigrationExecutor(connection)
    latest=executor.loader.graph.leaf_nodes()
    previous=[('school','0004_foundation_integrity')]
    try:
        executor.migrate(previous)
        apps=executor.loader.project_state(previous).apps
        tenant=apps.get_model('platform','Tenant').objects.create(name='Phase 3 migration',slug='phase3-migration')
        company=apps.get_model('settings_app','Company').objects.create(tenant_id=tenant.pk,name='School')
        branch=apps.get_model('settings_app','Branch').objects.create(tenant_id=tenant.pk,company_id=company.pk,name='Campus',code='P3')
        year=apps.get_model('school','AcademicYear').objects.create(tenant_id=tenant.pk,branch_id=branch.pk,name='Current',code='CURRENT',start_date='2026-01-01',end_date='2026-12-31',status='active',is_current=True)
        MigrationExecutor(connection).migrate(latest)
        from apps.school.models import AcademicYear, Student
        current=AcademicYear.objects.get(pk=year.pk)
        assert current.tenant_id==tenant.pk and current.branch_id==branch.pk
        assert current.is_current and current.code=='CURRENT'
        assert not Student.objects.exists()
        # Disposable empty SIS rollback only; production SIS records would be lost.
        MigrationExecutor(connection).migrate(previous)
        old=MigrationExecutor(connection).loader.project_state(previous).apps
        assert old.get_model('school','AcademicYear').objects.get(pk=year.pk).is_current
    finally:
        MigrationExecutor(connection).migrate(latest)
