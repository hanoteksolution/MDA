import { describe, expect, it, vi } from 'vitest';

// Page modules import the auth store, which reads localStorage at import time.
vi.hoisted(() => {
 const values = new Map<string, string>();
 Object.assign(globalThis, { localStorage: { getItem: (k: string) => values.get(k) ?? null, setItem: (k: string, v: string) => void values.set(k, v), removeItem: (k: string) => void values.delete(k), clear: () => values.clear() } });
});
import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import { DataTable } from '@/components/data/DataTable';
import { SCHOOL_NAV_GROUPS } from '@/navigation/schoolNavigation';
import { listColumns, parentFilters } from './sis/ListPage';
import { detailFields, relatedLinks } from './sis/DetailPage';
import { AdmissionsOverview } from './sis/DashboardPage';
import { resources } from './sis/config';
import { singular, description, immutable, editable, WORKFLOW_ENTRY } from './sis/meta';
import { SchoolDashboardView, dashboardKpis, type DashboardData } from './pages/SchoolPage';
import { ErrorBanner, PermissionDenied, SchoolStatusBadge, statusTone } from './components/SchoolUi';
import type { Row } from './sis/api';

const html = (el: React.ReactElement) => renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
const student: Row = { id: 's1', name: 'Amina Yusuf', number: 'STU-001', branch_name: 'Main', current_class: 'Grade 4', status: 'active', admission_date: '2026-01-10' };

describe('School list pages (canonical DataTable)', () => {
 it('renders searchable, filterable, paginated students with row actions and status badges', () => {
  const columns = listColumns('students', false, () => [{ label: 'View details', to: '/school/sis/students/s1' }, { label: 'Edit', to: '/school/sis/students/s1/edit' }]);
  const out = html(<DataTable columns={columns} data={[student]} page={1} pageSize={25} total={1} onPageChange={() => undefined} searchValue="" onSearchChange={() => undefined} searchPlaceholder="Search students…" filters={[{ key: 'status', label: 'Status', value: '', options: [{ value: '', label: 'All statuses' }, { value: 'active', label: 'Active' }] }]}/>);
  expect(out).toContain('aria-label="Search students…"');
  expect(out).toContain('href="/school/sis/students/s1"');
  expect(out).toContain('>Amina Yusuf<');
  expect(out).toContain('aria-label="Actions for Amina Yusuf"');
  expect(out).toMatch(/bg-success\/10[^"]*"[^>]*>active</);
  expect(out).toContain('Admission date');
  expect(out).toContain('role="combobox"');
  expect(out).toMatch(/1\D+of\D+1|1 of 1|Showing/);
 });

 it('links archived rows to their archived detail view', () => {
  const [first] = listColumns('guardians', true, () => []);
  expect(html(<>{first.cell({ id: 'g1', name: 'Hodan', number: 'G-1' })}</>)).toContain('href="/school/sis/guardians/g1?archived=true"');
 });

 it('shows the canonical empty state', () => {
  const out = html(<DataTable columns={listColumns('students', false, () => [])} data={[]} emptyMessage="No students yet."/>);
  expect(out).toContain('role="status"');
  expect(out).toContain('No students yet.');
 });

 it('recognises parent filters from related-record links only', () => {
  expect(parentFilters(new URLSearchParams('student_id=1&branch_id=2&status=active&school_class_id=3'))).toEqual([['student_id', '1']]);
 });

 it('has header copy for every School resource', () => {
  for (const key of Object.keys(resources)) {
   expect(singular(key), key).not.toBe('Record');
   expect(description(key), key).not.toBe('');
  }
 });

 it('never offers generic edit/archive on workflow-owned records', () => {
  for (const key of ['decisions', 'transitions', 'marks', 'report-cards', 'attendance-sessions', 'billing-receipts']) {
   expect(immutable(key), key).toBe(true);
   expect(editable(key), key).toBe(false);
  }
  expect(editable('students')).toBe(true);
 });

 it('routes workflow-created lists to real workflow pages', () => {
  const routes = new Set(SCHOOL_NAV_GROUPS.flatMap(g => g.entries.map(e => e.to)));
  for (const [key, entry] of Object.entries(WORKFLOW_ENTRY)) {
   expect(resources[key], key).toBeDefined();
   expect(routes.has(entry.to), entry.to).toBe(true);
  }
 });
});

describe('School detail pages', () => {
 it('only shows related records the user may view', () => {
  const links = relatedLinks('students', 's1', child => child !== 'notes');
  expect(links.map(l => l.title)).toContain('Enrollments');
  expect(links.find(l => l.title === 'Enrollments')?.to).toBe('/school/sis/enrollments?student_id=s1');
  expect(links.some(l => l.title === 'Student notes')).toBe(false);
 });

 it('hides identifiers and structured payloads from the detail grid', () => {
  const labels = detailFields('students', { ...student, branch_id: 'b', photo_url: 'x', snapshot: { a: 1 }, middle_name: null }).map(f => f.label);
  expect(labels).toContain('Number');
  expect(labels).toContain('Middle');
  expect(labels.filter(l => l === 'Branch')).toHaveLength(1); // branch_name shown once, branch_id hidden
  expect(labels.some(l => /Photo|Snapshot|^Status$/.test(l))).toBe(false);
 });
});

describe('School feedback states', () => {
 it('uses one status vocabulary', () => {
  expect(statusTone('enrolled')).toBe('success');
  expect(statusTone('Under review')).toBe('warning');
  expect(statusTone('withdrawn')).toBe('destructive');
  expect(statusTone('closed')).toBe('secondary');
  expect(html(<SchoolStatusBadge status={null}/>)).toContain('—');
 });

 it('announces errors and permission denial accessibly', () => {
  expect(html(<ErrorBanner message="Boom" onRetry={() => undefined}/>)).toMatch(/role="alert".*Boom.*Retry/s);
  expect(html(<PermissionDenied message="No access."/>)).toMatch(/role="status".*Permission required.*No access\./s);
 });
});

const empty: DashboardData = { counts: {}, failed: [] };

describe('School dashboard', () => {
 it('shows skeletons while loading', () => {
  const out = html(<SchoolDashboardView data={empty} loading quickLinks={[]}/>);
  expect(out).toContain('animate-pulse');
  expect(out).not.toContain('Academic calendar');
 });

 it('never fabricates metrics the user cannot see', () => {
  expect(dashboardKpis(empty)).toEqual([]);
  const kpis = dashboardKpis({ ...empty, summary: { classes: 12, campuses: 2 }, counts: { students: 340 } });
  expect(kpis.map(k => [k.title, k.value])).toEqual([['Active students', '340'], ['Classes', '12'], ['Campuses', '2']]);
 });

 it('renders real sections, empty states and permission-aware panels', () => {
  const data: DashboardData = {
   ...empty,
   summary: { classes: 4, sections: 8, campuses: 1, active_terms: 1, current_years: [{ id: 'y1', name: '2026/27', branch_name: 'Main', start_date: '2026-09-01', end_date: '2027-06-30' }] },
   counts: { students: 120, staff: 9, pendingGrading: 3 },
   attendance: { count: 1, sessions: [{ id: 'a1', name: 'x', school_class_name: 'Grade 4', section_name: 'A', mode: 'daily', record_count: 30, absent_count: 2, status: 'submitted' }] },
  };
  const out = html(<SchoolDashboardView data={data} loading={false} quickLinks={[{ label: 'Take attendance', to: '/school/attendance', icon: null }]}/>);
  expect(out).toContain('aria-label="Active students: 120"');
  expect(out).toContain('aria-label="Attendance registers today: 1/1"');
  expect(out).toContain('2026/27');
  expect(out).toContain('1 register · 2 absent');
  expect(out).toContain('Submissions awaiting grading');
  expect(out).toContain('href="/school/attendance"');
  expect(out).not.toContain('Recent admissions');
  expect(out).not.toContain('Open admissions');
 });

 it('explains missing data instead of hiding the calendar', () => {
  const out = html(<SchoolDashboardView data={{ ...empty, summary: { current_years: [] } }} loading={false} quickLinks={[]}/>);
  expect(out).toContain('No current academic year');
  expect(out).not.toContain("Today's attendance"); // hidden without attendance access
  expect(out).not.toContain('Quick actions');
 });
});

describe('Admissions overview', () => {
 it('summarises the pipeline from API values only', () => {
  const out = html(<AdmissionsOverview data={{ total_applications: 10, new_applications: 2, under_review: 3, accepted: 1, waitlisted: 1, rejected: 1, enrolled: 2, pending_documents: 4, conversion_rate: 20, assessment_scheduled: null, interview_scheduled: 0, recent_applications: [{ id: 'p1', name: 'APP-1', applicant_name: 'Ali', status: 'under_review' }], missing_documents: [], upcoming_interviews: [], by_class: [{ school_class__name: 'Grade 1', count: 3 }] }}/>);
  expect(out).toMatch(/Open applications.*?>7</s);
  expect(out).toContain('href="/school/sis/applications/p1"');
  expect(out).toContain('All required documents are verified.');
  expect(out).toContain('No interviews scheduled.');
  expect(out).toContain('Grade 1');
  expect(out).not.toContain('Assessments scheduled');
  expect(out).toContain('Interviews scheduled');
 });
});
