"""Run only after the Phase 4 tests, against their disposable PostgreSQL database."""
import json
from pathlib import Path
from django.conf import settings
from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from tests.unit.test_school_foundation import school
from tests.unit.test_school_sis import sis, direct
from tests.unit.test_school_ops import ops

assert settings.DATABASES['default']['NAME'] == 'test_school_phase3_verify'
bootstrap_roles_and_permissions()
s = ops.__wrapped__(sis.__wrapped__(school.__wrapped__(None)))
for name in ('Amina', 'Bilal', 'Chidi'):
    direct(s, first_name=name)
s['assign'](s['p1_staff'], None, role='class_teacher')
for user in (s['owner'], s['teacher_user']):
    user.set_password('LocalPhase4Only123!')
    user.save()
Path('/tmp/school-phase4-browser-fixture.json').write_text(json.dumps({
    'branch': str(s['a'].pk), 'year': str(s['y'].pk), 'klass': str(s['k'].pk), 'section': str(s['sec'].pk),
    'version': str(s['version'].pk), 'p1': str(s['p1'].pk), 'p2': str(s['p2'].pk), 'room1': str(s['room1'].pk), 'room2': str(s['room2'].pk),
    'math': str(s['math'].pk), 'sci': str(s['sci'].pk), 'staff1': str(s['p1_staff'].pk), 'staff2': str(s['p2_staff'].pk),
    'teacher': s['teacher_user'].username,
}))
print('Disposable Phase 4 browser fixture ready.')
