import type { Row, RosterStudent, Values } from './api';
export const ATTENDANCE_STATUSES = ['present','absent','late','excused','half_day'] as const;
export const WEEKDAYS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
export type Mark = { student_id: string; student_name: string; roll_number: string; status: string; remarks: string };
export const toMarks = (students: RosterStudent[]): Mark[] => students.map(s => ({student_id:s.student_id, student_name:s.student_name, roll_number:s.roll_number, status:s.status ?? '', remarks:s.remarks ?? ''}));
export const markAll = (marks: Mark[], status: string): Mark[] => marks.map(m => ({...m, status}));
export const unmarked = (marks: Mark[]) => marks.filter(m => !m.status).length;
export const tally = (marks: Mark[]) => Object.fromEntries(ATTENDANCE_STATUSES.map(s => [s, marks.filter(m => m.status === s).length]));
/** Only marked students are sent; a submit is refused server-side unless everyone is marked. */
export function attendancePayload(slot: Values, marks: Mark[], submit: boolean): Values {
 const data: Values = {};
 for (const [key, value] of Object.entries(slot)) if (value !== '' && value !== undefined && value !== null) data[key] = value;
 if (data.mode !== 'period') { delete data.period_id; delete data.subject_offering_id; }
 delete data.branch_id;
 return {...data, records: marks.filter(m => m.status).map(m => ({student_id:m.student_id, status:m.status, remarks:m.remarks})), submit};
}
export const slotReady = (slot: Values) => Boolean(slot.school_class_id && slot.date && (slot.mode !== 'period' || slot.period_id));
export interface GridCell { weekday: number; periodId: string; entries: Row[] }
/** Rows are periods in clock order; a cell holds every lesson in that weekday/period slot. */
export function timetableGrid(periods: Row[], entries: Row[], weekdays: number[] = [1,2,3,4,5]) {
 const ordered = [...periods].sort((a, b) => String(a.start_time).localeCompare(String(b.start_time)));
 return ordered.map(period => ({period, cells: weekdays.map(weekday => ({weekday, periodId: period.id, entries: entries.filter(e => Number(e.weekday) === weekday && e.period_id === period.id)}))}));
}
export const lessonLabel = (e: Row) => [e.school_class_name, e.section_name, e.subject_offering_name].filter(Boolean).join(' · ') + (e.staff_name ? ` — ${e.staff_name}` : '') + (e.classroom_name ? ` (${e.classroom_name})` : '');
