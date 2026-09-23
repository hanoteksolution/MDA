"""Student lifecycle permissions; ordinary role names never enter domain rules."""
RESOURCES = {
    'applicants':'applicant', 'applications':'admission', 'assessments':'assessment',
    'interviews':'interview', 'decisions':'decision', 'document-types':'document_type',
    'applicant-documents':'admission_document', 'students':'student', 'families':'family',
    'guardians':'guardian', 'relationship-types':'relationship_type',
    'student-guardians':'student_guardian', 'applicant-guardians':'applicant_guardian',
    'enrollments':'enrollment', 'transitions':'student_transition',
    'student-documents':'student_document', 'emergency-contacts':'emergency_contact',
    'notes':'student_note', 'admission-policies':'admission_policy',
}
SIS_PERMISSIONS = [(f'school.{r}.{a}', f'School {r.replace("_", " ")}: {a}', 'school') for r in RESOURCES.values() for a in ('view','create','update','archive','restore','export')]
SIS_PERMISSIONS += [(f'school.{r}.{a}', f'School {r}: {a}', 'school') for r,actions in {
    'admission':('submit','review','assess','interview','decide','override_document_requirement','enroll','withdraw'),
    'student':('create_direct','transfer','withdraw','reenroll','promote','repeat','graduate','change_status','override_capacity','audit'),
    'admission_document':('verify',), 'student_document':('verify',),
    'student_note_confidential':('view','update'),
}.items() for a in actions]

from .ops_permissions import RESOURCES as _OPS_RESOURCES, OPS_PERMISSIONS
RESOURCES.update(_OPS_RESOURCES)
SIS_PERMISSIONS += OPS_PERMISSIONS

from .learning_contracts import RESOURCES as LEARNING_RESOURCES, PERMISSIONS as LEARNING_PERMISSIONS
RESOURCES.update(LEARNING_RESOURCES)
SIS_PERMISSIONS += LEARNING_PERMISSIONS

from .fee_contracts import RESOURCES as FEE_RESOURCES, PERMISSIONS as FEE_PERMISSIONS
RESOURCES.update(FEE_RESOURCES)
SIS_PERMISSIONS += FEE_PERMISSIONS
