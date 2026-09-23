"""Phase 5 locks, idempotency and additive migration on PostgreSQL."""
import pytest
from django.db import connection,transaction,IntegrityError
from apps.school.models.learning import Mark,ResultPublication,ReportCardVersion
from apps.school.services import marks_service as marks,promotion_service as promotion
from tests.unit.test_school_learning import school_catalog,school,sis,learning,save
from tests.unit.test_school_postgresql import race

pytestmark=pytest.mark.django_db(transaction=True)

@pytest.fixture(autouse=True)
def require_pg():
    if connection.vendor!='postgresql':pytest.skip('Real PostgreSQL concurrency gate.')

def test_mark_publish_promotion_races(learning):
    s=learning;base='/api/v1/school/sis/'
    payload={'expected_revision':s['exam'].revision,'records':[{'enrollment_id':str(s['enrollment'].pk),'score':'80'}]}
    r=race(s['owner'],[(base+f"academic-assessments/{s['assessment'].pk}/marks/",payload)]*2)
    assert sorted(code for code,_ in r)==[200,400],r
    assert Mark.objects.count()==1
    s['exam'].refresh_from_db()
    for action in ('submit','moderate'):marks.exam_action(s['exam'].pk,action,{'expected_revision':s['exam'].revision},access=s['access'])
    r=race(s['owner'],[(base+f"exams/{s['exam'].pk}/publish/",{'expected_revision':s['exam'].revision})]*2)
    assert [code for code,_ in r]==[200,200],r
    assert ResultPublication.objects.count()==ReportCardVersion.objects.count()==1
    pub=ResultPublication.objects.get();batch=promotion.preview({'publication_id':str(pub.pk),'effective_date':'2026-09-20','reason':'Graduation','items':[{'enrollment_id':str(s['enrollment'].pk),'outcome':'graduate'}]},access=s['access'])
    r=race(s['owner'],[(base+f'promotion-batches/{batch.pk}/commit/',{'fingerprint':batch.fingerprint})]*2)
    assert [code for code,_ in r]==[200,200],r
    from apps.school.models import StudentTransition
    assert StudentTransition.objects.filter(outcome='graduated').count()==1
    with pytest.raises(IntegrityError),transaction.atomic():Mark.objects.filter(pk=Mark.objects.get().pk).update(score=-1)


def test_phase5_migration_forward_and_empty_reverse():
    from django.db.migrations.executor import MigrationExecutor
    executor=MigrationExecutor(connection);latest=executor.loader.graph.leaf_nodes();previous=[('school','0006_attendancecorrection_attendancerecord_and_more')]
    # Resolve the existing Phase 4 migration by its dependency, without guessing its name.
    previous=executor.loader.get_migration('school','0007_phase5').dependencies
    previous=[item for item in previous if item[0]=='school']
    try:
        executor.migrate(previous)
        apps=MigrationExecutor(connection).loader.project_state(previous).apps
        tenant=apps.get_model('platform','Tenant').objects.create(name='Phase5',slug='phase5-migration')
        company=apps.get_model('settings_app','Company').objects.create(tenant_id=tenant.pk,name='School')
        branch=apps.get_model('settings_app','Branch').objects.create(tenant_id=tenant.pk,company_id=company.pk,name='Campus',code='P5')
        student=apps.get_model('school','Student').objects.create(tenant_id=tenant.pk,branch_id=branch.pk,first_name='Preserved',date_of_birth='2015-01-01',number='S-P5',admission_date='2026-01-01')
        MigrationExecutor(connection).migrate(latest)
        from apps.school.models import Student
        assert Student.objects.get(pk=student.pk).first_name=='Preserved'
        assert not Mark.objects.exists()
        MigrationExecutor(connection).migrate(previous)
        old=MigrationExecutor(connection).loader.project_state(previous).apps
        assert old.get_model('school','Student').objects.filter(pk=student.pk).exists()
    finally:MigrationExecutor(connection).migrate(latest)
