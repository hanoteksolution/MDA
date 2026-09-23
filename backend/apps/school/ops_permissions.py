"""Teaching-staff, timetable and attendance permissions (merged into the SIS catalog)."""
RESOURCES = {
    'employees': 'employee', 'staff-profiles': 'staff_profile', 'teacher-assignments': 'teacher_assignment',
    'classrooms': 'classroom', 'periods': 'period', 'timetable-versions': 'timetable', 'timetable-entries': 'timetable_entry',
    'attendance-sessions': 'attendance', 'attendance-records': 'attendance_record', 'attendance-corrections': 'attendance_correction',
}
READ_ONLY = ('attendance_record', 'attendance_correction')
OPS_PERMISSIONS = [
    (f'school.{r}.{a}', f'School {r.replace("_", " ")}: {a}', 'school')
    for r in RESOURCES.values() for a in (('view',) if r in READ_ONLY else ('view', 'create', 'update', 'archive', 'restore'))
    if r != 'attendance'
] + [
    ('school.attendance.view', 'School attendance: view', 'school'),
    # take = record/submit attendance for classes the user is assigned to; take_any = any accessible class.
    ('school.attendance.take', 'School attendance: take for assigned classes', 'school'),
    ('school.attendance.take_any', 'School attendance: take for any accessible class', 'school'),
    ('school.timetable.publish', 'School timetable: publish', 'school'),
    ('school.attendance_correction.request', 'School attendance corrections: request', 'school'),
    ('school.attendance_correction.approve', 'School attendance corrections: approve or reject', 'school'),
]
