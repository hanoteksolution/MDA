export type SchoolValue = string | number | boolean | null;
export interface SchoolRecord {
    id: string;
    [key: string]: unknown;
}
export interface Field {
    key: string;
    label: string;
    type?: 'text' | 'date' | 'time' | 'number' | 'checkbox' | 'email' | 'url' | 'select' | 'relation';
    options?: string[];
    resource?: string;
    required?: boolean;
    group?: string;
    immutable?: boolean;
    default?: SchoolValue;
}
export interface Resource {
    title: string;
    singular: string;
    permission: string;
    description: string;
    campus?: boolean;
    period?: boolean;
    fields: Field[];
}
const text = (key: string, label: string, required = false): Field => ({ key, label, required });
const rel = (key: string, label: string, resource: string, required = false, immutable = false): Field => ({ key, label, resource, required, immutable, type: 'relation' });
const number = (key: string, label: string, value = 1): Field => ({ key, label, type: 'number', default: value });
const status: Field = { key: 'status', label: 'Status', type: 'select', options: ['active', 'inactive'], default: 'active' };
const base: Field[] = [text('name', 'Name', true), text('code', 'Code', true)];
const description = text('description', 'Notes');
const campus = rel('branch_id', 'Campus', 'lookups/campuses', true, true);
const dates: Field[] = [{ key: 'start_date', label: 'Start date', type: 'date', required: true }, { key: 'end_date', label: 'End date', type: 'date', required: true }];
const marks: Field[] = [number('maximum_marks', 'Maximum marks', 100), number('pass_mark', 'Pass mark', 50), number('weight', 'Weight'), { key: 'mandatory', label: 'Mandatory', type: 'checkbox', default: true }];
const teacher = rel('teacher_id', 'Teacher', 'lookups/teachers');
export const resources: Record<string, Resource> = {
    'academic-years': { title: 'Academic years', singular: 'Academic year', permission: 'academic_year', description: 'Manage campus calendars and controlled academic lifecycle actions.', campus: true, period: true, fields: [...base, campus, ...dates, { key: 'admission_open', label: 'Admissions open', type: 'checkbox' }, { key: 'enrollment_open', label: 'Enrollment open', type: 'checkbox' }, description] },
    terms: { title: 'Terms & semesters', singular: 'Term', permission: 'term', description: 'Define teaching periods, exam windows and publication dates.', campus: true, period: true, fields: [...base, campus, rel('academic_year_id', 'Academic year', 'academic-years', true, true), number('sort_order', 'Sequence'), ...dates, { key: 'exam_start', label: 'Exam start', type: 'date' }, { key: 'exam_end', label: 'Exam end', type: 'date' }, { key: 'result_publish_date', label: 'Result publication', type: 'date' }] },
    levels: { title: 'Education levels', singular: 'Education level', permission: 'level', description: 'A reusable school-wide hierarchy, configured for your education system.', fields: [...base, number('sequence', 'Sequence'), description, status] },
    classes: { title: 'Classes & grades', singular: 'Class', permission: 'class', description: 'Organize grades by education level and campus.', campus: true, fields: [...base, campus, rel('education_level_id', 'Education level', 'levels', true), number('sequence', 'Sequence'), number('capacity', 'Capacity', 30), text('room', 'Default room'), teacher, description, status] },
    sections: { title: 'Sections & streams', singular: 'Section', permission: 'section', description: 'Manage class groups, capacity and homeroom assignments.', campus: true, fields: [...base, campus, rel('school_class_id', 'Class', 'classes', true, true), number('capacity', 'Capacity', 30), text('room', 'Room'), teacher, rel('shift_id', 'Shift', 'shifts'), description, status] },
    shifts: { title: 'School shifts', singular: 'Shift', permission: 'shift', description: 'Configure campus operating hours for future scheduling.', campus: true, fields: [...base, campus, { key: 'start_time', label: 'Start time', type: 'time', required: true }, { key: 'end_time', label: 'End time', type: 'time', required: true }, description, status] },
    subjects: { title: 'Subjects', singular: 'Subject', permission: 'subject', description: 'Maintain a reusable subject catalog across classes and campuses.', fields: [...base, text('short_name', 'Short name'), rel('category_id', 'Category', 'subject-categories'), ...marks, { key: 'teaching_mode', label: 'Teaching mode', type: 'select', options: ['theory', 'practical', 'mixed'], default: 'theory' }, description, status] },
    'subject-categories': { title: 'Subject categories', singular: 'Subject category', permission: 'subject_category', description: 'Group subjects using your own academic categories.', fields: [...base, description, status] },
    'subject-offerings': { title: 'Subject offerings', singular: 'Subject offering', permission: 'subject_offering', description: 'Connect subjects to a year, campus, class and optional section.', campus: true, fields: [...base, campus, rel('academic_year_id', 'Academic year', 'academic-years', true, true), rel('term_id', 'Term', 'terms'), rel('school_class_id', 'Class', 'classes', true, true), rel('section_id', 'Section', 'sections'), rel('subject_id', 'Subject', 'subjects', true), teacher, ...marks, number('weekly_periods', 'Weekly periods'), description, status] },
    campuses: { title: 'Campuses', singular: 'Campus', permission: 'campus', description: 'Manage the shared ERP branches used by your school.', fields: [...base, rel('company_id', 'Company', 'lookups/companies', true, true), text('address', 'Address'), text('phone', 'Phone'), { key: 'email', label: 'Email', type: 'email' }, { key: 'is_default', label: 'Main campus', type: 'checkbox' }] },
    'campus-access': { title: 'Campus access', singular: 'Campus access grant', permission: 'campus_access', description: 'Grant or revoke additional campus access without changing a user’s role.', campus: true, fields: [campus, rel('user_id', 'User', 'lookups/users', true, true), { key: 'is_active', label: 'Access enabled', type: 'checkbox', default: true }] },
};
export const profileFields: Field[] = [campus, text('school_name', 'School name', true), text('display_name', 'Display name'), text('school_code', 'School code'), text('registration_number', 'Registration number'), text('authority_reference', 'Education authority reference'), { key: 'school_type', label: 'School type', type: 'select', options: ['primary', 'secondary', 'k12', 'training', 'other'] }, rel('principal_user_id', 'Principal', 'lookups/principals'), text('logo_url', 'Logo URL'), text('phone', 'Phone'), { key: 'email', label: 'Email', type: 'email' }, { key: 'website', label: 'Website', type: 'url' }, text('address', 'Campus address'), text('city', 'City'), text('country', 'Country'), text('timezone', 'Timezone', true), text('currency', 'Accounting currency', true), text('language', 'Primary language', true), { key: 'academic_calendar_type', label: 'Academic calendar', type: 'select', options: ['terms', 'semesters', 'custom'] }, text('term_label', 'Period label (Term, Semester, Quarter…)'), { key: 'allow_term_overlap', label: 'Allow overlapping terms', type: 'checkbox' }, text('grading_scheme', 'Default grading scheme reference'), { key: 'attendance_mode', label: 'Attendance mode', type: 'select', options: ['daily', 'period', 'both'] }, { ...status, options: ['active', 'inactive'] }];
export const schoolPath = (resource: string) => `/school/academics/${resource}`;
export function formPayload(fields: Field[], values: SchoolRecord | Record<string, unknown>) {
    const data: Record<string, unknown> = {};
    for (const f of fields) {
        const v = values[f.key];
        if (v === undefined)
            continue;
        data[f.key] = f.type === 'checkbox' ? Boolean(v) : f.type === 'relation' || f.type === 'date' || f.type === 'time' ? (v || null) : v;
    }
    return data;
}
export function lifecycleActions(resource: Resource, row: SchoolRecord, can: (action: string) => boolean) {
    if (row.deleted_at || (resource.permission === 'campus' && row.is_active === false))
        return can('restore') ? ['restore'] : [];
    const actions: string[] = [];
    if (resource.period && ['planning', 'active'].includes(String(row.status))) {
        if (can('activate') && !row.is_current && (row.status === 'planning' || resource.permission === 'academic_year'))
            actions.push('activate');
        if (can('close'))
            actions.push('close');
    }
    if (can('archive'))
        actions.push('archive');
    return actions;
}
