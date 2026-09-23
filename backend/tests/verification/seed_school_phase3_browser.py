"""Run only after Phase 3 tests, against their disposable PostgreSQL database."""
import json
from pathlib import Path
from django.conf import settings
from apps.authentication.bootstrap import bootstrap_roles_and_permissions
from tests.unit.test_school_foundation import school
from tests.unit.test_school_sis import sis

assert settings.DATABASES['default']['NAME'] == 'test_school_phase3_verify'
bootstrap_roles_and_permissions()
s = sis.__wrapped__(school.__wrapped__(None))
s['owner'].set_password('LocalPhase3Only123!')
s['owner'].save()
Path('/tmp/school-phase3-browser-fixture.json').write_text(json.dumps({
    'branch': str(s['a'].pk), 'year': str(s['y'].pk),
    'klass': str(s['k'].pk), 'section': str(s['sec'].pk),
}))
print('Disposable Phase 3 browser fixture ready.')
