"""Upgrade existing calendar records without resetting IDs or dates."""
import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

@pytest.mark.django_db(transaction=True)
def test_existing_school_upgrade():
    executor=MigrationExecutor(connection)
    latest=executor.loader.graph.leaf_nodes()
    target=[('school','0001_initial')]
    try:
        executor.migrate(target)
        apps=executor.loader.project_state(target).apps
        Tenant=apps.get_model('platform','Tenant');Company=apps.get_model('settings_app','Company');Branch=apps.get_model('settings_app','Branch')
        preserved = []
        Year = apps.get_model('school', 'AcademicYear')
        Term = apps.get_model('school', 'AcademicTerm')
        Profile = apps.get_model('school', 'SchoolProfile')
        for tenant_number in range(3):
            tenant = Tenant.objects.create(name=f'Migration school {tenant_number}', slug=f'school-migration-{tenant_number}')
            company = Company.objects.create(tenant_id=tenant.pk, name='School')
            for campus_number in range(3):
                branch = Branch.objects.create(tenant_id=tenant.pk, company_id=company.pk, name=f'Campus {campus_number}', code=f'MIG-{campus_number}')
                year = Year.objects.create(tenant_id=tenant.pk, branch_id=branch.pk, name='2026', start_date='2026-01-01', end_date='2026-12-31', status='active', is_current=True)
                term = Term.objects.create(tenant_id=tenant.pk, branch_id=branch.pk, academic_year_id=year.pk, name='Term 1', start_date='2026-01-01', end_date='2026-05-01', sort_order=0)
                profile = Profile.objects.create(tenant_id=tenant.pk, branch_id=branch.pk, school_name='Original school')
                preserved.append((tenant.pk, branch.pk, year.pk, term.pk, profile.pk))
        executor = MigrationExecutor(connection)
        executor.migrate(latest)
        from apps.school.models import AcademicYear, AcademicTerm, SchoolProfile
        for tenant_id, branch_id, year_id, term_id, profile_id in preserved:
            new_year = AcademicYear.objects.get(pk=year_id)
            assert new_year.code and new_year.is_current and str(new_year.start_date) == '2026-01-01'
            assert new_year.tenant_id == tenant_id and new_year.branch_id == branch_id
            new_term = AcademicTerm.objects.get(pk=term_id)
            assert new_term.sort_order == 1 and new_term.academic_year_id == year_id
            assert new_term.tenant_id == tenant_id and new_term.branch_id == branch_id
            assert SchoolProfile.objects.get(pk=profile_id).school_name == 'Original school'
        assert AcademicYear.objects.filter(pk__in=[row[2] for row in preserved]).count() == 9
        assert len(set(AcademicYear.objects.filter(pk__in=[row[2] for row in preserved]).values_list('code', flat=True))) == 9
        # A disposable rollback removes Phase 2 schema; baseline rows must survive.
        MigrationExecutor(connection).migrate(target)
        historical = MigrationExecutor(connection).loader.project_state(target).apps
        assert historical.get_model('school', 'AcademicYear').objects.filter(pk__in=[row[2] for row in preserved]).count() == 9
        assert historical.get_model('school', 'AcademicTerm').objects.filter(pk__in=[row[3] for row in preserved]).count() == 9
        assert historical.get_model('school', 'SchoolProfile').objects.filter(pk__in=[row[4] for row in preserved]).count() == 9
    finally:
        MigrationExecutor(connection).migrate(latest)
