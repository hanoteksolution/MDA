import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { GraduationCap, Building2, Layers, Users, ClipboardList, Presentation, CalendarCheck, ClipboardCheck, Plus, CalendarDays, Settings } from 'lucide-react';
import { PageLayout } from '@/components/layout/PageLayout';
import { ContentSection } from '@/components/layout/ContentSection';
import { EmptyState } from '@/components/layout/EmptyState';
import { KpiCard, KpiGrid } from '@/components/data/KpiCard';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { schoolApi } from '@/services/api/school';
import { cn } from '@/utils/cn';
import { useSisPermissions } from '../sis/store';
import { sisApi, type Params, type Row, type Values } from '../sis/api';
import { path as sisPath, text } from '../sis/config';
import { useCapabilities } from '../hooks/useFoundation';
import { useLookupOptions } from '../hooks/useLookupOptions';
import { schoolPath, type SchoolRecord } from '../foundation';
import { ErrorBanner, SchoolStatusBadge } from '../components/SchoolUi';

type Count = 'students' | 'staff' | 'openAssignments' | 'pendingGrading' | 'examsAwaiting';
export interface DashboardData {
    summary?: Record<string, unknown>;
    counts: Partial<Record<Count, number>>;
    attendance?: { sessions: Row[]; count: number };
    admissions?: Values;
    failed: string[];
}
export type QuickLink = { label: string; to: string; icon: React.ReactNode };

const today = () => new Date().toLocaleDateString('en-CA');
const n = (value: unknown) => (typeof value === 'number' ? value.toLocaleString() : undefined);

/** Loads only what the user may see; each source fails independently. */
function useSchoolDashboard(branch: string, codes: string[], ready: boolean, attempt: number) {
    const [data, setData] = useState<DashboardData>({ counts: {}, failed: [] });
    const [loading, setLoading] = useState(true);
    const key = codes.join(',');
    useEffect(() => {
        if (!ready) return;
        let active = true; setLoading(true);
        const has = (code: string) => codes.includes(code);
        const scope = branch ? { branch_id: branch } : {};
        const next: DashboardData = { counts: {}, failed: [] };
        const count = (name: Count, resource: string, params: Values) => sisApi.list(resource, { ...scope, ...params, page_size: 1 } as Params).then(r => { next.counts[name] = r.data.count; });
        const jobs: [string, Promise<unknown>][] = [['School summary', schoolApi.summary(branch || undefined).then(r => { next.summary = r.data; })]];
        if (has('school.student.view')) jobs.push(['Students', count('students', 'students', { status: 'active' })]);
        if (has('school.staff_profile.view')) jobs.push(['Teaching staff', count('staff', 'staff-profiles', { status: 'active' })]);
        if (has('school.assignment.view')) jobs.push(['Assignments', count('openAssignments', 'assignments', { status: 'published' })]);
        if (has('school.submission.view')) jobs.push(['Submissions', count('pendingGrading', 'submissions', { status: 'submitted' })]);
        if (has('school.exam.view')) jobs.push(['Exams', count('examsAwaiting', 'exams', { status: 'submitted' })]);
        if (has('school.attendance.view')) jobs.push(['Attendance', sisApi.list('attendance-sessions', { ...scope, date__gte: today(), date__lte: today(), page_size: 100 }).then(r => { next.attendance = { sessions: r.data.results, count: r.data.count }; })]);
        if (has('school.admission.view')) jobs.push(['Admissions', sisApi.dashboard(scope).then(r => { next.admissions = r.data; })]);
        Promise.all(jobs.map(([name, job]) => job.catch(() => { next.failed.push(name); }))).then(() => { if (active) { setData(next); setLoading(false); } });
        return () => { active = false; };
    }, [branch, key, ready, attempt]);
    return { data, loading };
}

function openAdmissions(admissions?: Values) {
    if (!admissions) return undefined;
    return ['new_applications', 'under_review', 'accepted', 'waitlisted'].reduce((sum, k) => sum + (Number(admissions[k]) || 0), 0);
}

export function dashboardKpis(data: DashboardData) {
    const s = data.summary || {};
    const attendance = data.attendance;
    const submitted = attendance?.sessions.filter(x => x.status === 'submitted').length;
    return ([
        { key: 'students', title: 'Active students', value: n(data.counts.students), icon: <Users className="h-5 w-5"/>, to: sisPath('students') },
        { key: 'admissions', title: 'Open admissions', value: n(openAdmissions(data.admissions)), icon: <ClipboardList className="h-5 w-5"/>, to: '/school/admissions' },
        { key: 'staff', title: 'Teaching staff', value: n(data.counts.staff), icon: <Presentation className="h-5 w-5"/>, to: sisPath('staff-profiles') },
        { key: 'classes', title: 'Classes', value: n(s.classes), icon: <GraduationCap className="h-5 w-5"/>, to: schoolPath('classes') },
        { key: 'sections', title: 'Sections', value: n(s.sections), icon: <Layers className="h-5 w-5"/>, to: schoolPath('sections') },
        { key: 'campuses', title: 'Campuses', value: n(s.campuses), icon: <Building2 className="h-5 w-5"/>, to: schoolPath('campuses') },
        { key: 'attendance', title: 'Attendance registers today', value: attendance ? `${submitted}/${attendance.count}` : undefined, icon: <CalendarCheck className="h-5 w-5"/>, to: sisPath('attendance-sessions') },
        { key: 'grading', title: 'Submissions to grade', value: n(data.counts.pendingGrading), icon: <ClipboardCheck className="h-5 w-5"/>, to: `${sisPath('submissions')}?status=submitted` },
    ]).filter(k => k.value !== undefined);
}

export function SchoolDashboardView({ data, loading, quickLinks }: { data: DashboardData; loading: boolean; quickLinks: QuickLink[] }) {
    if (loading) return <KpiGrid columns={4}>{[0, 1, 2, 3].map(i => <KpiCard key={i} index={i} title="Loading" value="—" loading/>)}</KpiGrid>;
    const kpis = dashboardKpis(data);
    const years = (data.summary?.current_years || []) as SchoolRecord[];
    const sessions = data.attendance?.sessions || [];
    const recent = ((data.admissions?.recent_applications || []) as Row[]).slice(0, 5);
    const absent = sessions.reduce((sum, x) => sum + (Number(x.absent_count) || 0), 0);
    const activity = ([
        ['Published assignments', data.counts.openAssignments, `${sisPath('assignments')}?status=published`],
        ['Submissions awaiting grading', data.counts.pendingGrading, `${sisPath('submissions')}?status=submitted`],
        ['Exams awaiting moderation', data.counts.examsAwaiting, `${sisPath('exams')}?status=submitted`],
        ['Active terms', data.summary?.active_terms, schoolPath('terms')],
        ['Subject offerings', data.summary?.subject_offerings, schoolPath('subject-offerings')],
        ['Active teacher assignments', data.summary?.teacher_assignments, schoolPath('subject-offerings')],
    ] as const).filter(([, value]) => typeof value === 'number');
    return <>
        {kpis.length > 0 && <KpiGrid columns={kpis.length === 5 ? 5 : kpis.length === 3 || kpis.length === 6 ? 3 : 4}>{kpis.map((k, i) => <Link key={k.key} to={k.to} className="rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" aria-label={`${k.title}: ${k.value}`}><KpiCard index={i} title={k.title} value={k.value!} icon={k.icon}/></Link>)}</KpiGrid>}
        <div className={cn('grid gap-4', data.attendance && 'xl:grid-cols-3')}>
            <ContentSection title="Academic calendar" description="Current academic years" index={1} action={<Button asChild size="sm" variant="ghost"><Link to={schoolPath('academic-years')}>Manage</Link></Button>}>
                {years.length ? <ul className="divide-y">{years.map(y => <li key={y.id} className="py-2.5"><Link to={`${schoolPath('academic-years')}/${y.id}`} className="block text-sm"><span className="font-medium text-primary">{String(y.name)}</span><span className="block text-xs text-muted-foreground">{String(y.branch_name ?? '')} · {String(y.start_date)} – {String(y.end_date)}</span></Link></li>)}</ul>
                    : <EmptyState compact icon={<CalendarDays className="h-5 w-5"/>} title="No current academic year" description="Mark an academic year as current to drive terms, enrollment and attendance."/>}
            </ContentSection>
            {data.attendance && <div className="xl:col-span-2"><ContentSection title="Today's attendance" description={data.attendance ? `${sessions.length} register${sessions.length === 1 ? '' : 's'} · ${absent} absent` : undefined} index={2} action={<Button asChild size="sm" variant="ghost"><Link to="/school/attendance">Take attendance</Link></Button>}>
                {sessions.length ? <ul className="divide-y">{sessions.slice(0, 6).map(x => <li key={x.id} className="flex items-center justify-between gap-3 py-2.5 text-sm"><Link to={`${sisPath('attendance-sessions')}/${x.id}`} className="min-w-0"><span className="block truncate font-medium text-primary">{[x.school_class_name, x.section_name].filter(Boolean).map(text).join(' · ')}</span><span className="block text-xs text-muted-foreground">{text(x.mode)}{x.period_name ? ` · ${text(x.period_name)}` : ''} · {Number(x.record_count) || 0} marked · {Number(x.absent_count) || 0} absent</span></Link><SchoolStatusBadge status={x.status}/></li>)}</ul>
                        : <EmptyState compact icon={<CalendarCheck className="h-5 w-5"/>} title="No attendance registers yet today."/>}
            </ContentSection></div>}
        </div>
        <div className="grid gap-4 md:grid-cols-[repeat(auto-fit,minmax(320px,1fr))]">
            {data.admissions && <ContentSection title="Recent admissions" index={3} action={<Button asChild size="sm" variant="ghost"><Link to={sisPath('applications')}>View all</Link></Button>}>
                {recent.length ? <ul className="divide-y">{recent.map(a => <li key={a.id} className="py-2.5"><Link to={`${sisPath('applications')}/${a.id}`} className="flex items-center justify-between gap-3 text-sm"><span className="min-w-0"><span className="block truncate font-medium text-primary">{text(a.applicant_name || a.name)}</span><span className="block truncate text-xs text-muted-foreground">{[a.school_class_name, a.application_date].filter(Boolean).map(text).join(' · ')}</span></span><SchoolStatusBadge status={a.status}/></Link></li>)}</ul> : <EmptyState compact title="No applications yet."/>}
            </ContentSection>}
            {activity.length > 0 && <ContentSection title="Academic activity" index={4}>
                <ul className="divide-y">{activity.map(([title, value, to]) => <li key={title}><Link to={to} className="flex items-center justify-between py-2.5 text-sm hover:text-primary"><span>{title}</span><span className="font-semibold tabular-nums">{Number(value).toLocaleString()}</span></Link></li>)}</ul>
            </ContentSection>}
            {quickLinks.length > 0 && <ContentSection title="Quick actions" index={5}>
                <div className="grid gap-2">{quickLinks.map(q => <Button key={q.to} asChild variant="outline" className="justify-start"><Link to={q.to}>{q.icon}{q.label}</Link></Button>)}</div>
            </ContentSection>}
        </div>
    </>;
}

export function SchoolPage() {
    const [branch, setBranch] = useState('');
    const [attempt, setAttempt] = useState(0);
    const { can } = useCapabilities();
    const sis = useSisPermissions();
    const campuses = useLookupOptions('lookups/campuses', {}, 'All campuses');
    const { data, loading } = useSchoolDashboard(branch, sis.codes, sis.loaded, attempt);
    const icon = (Icon: typeof Plus) => <Icon className="mr-2 h-4 w-4"/>;
    const quickLinks: QuickLink[] = [
        ...(sis.can('applications', 'create') ? [{ label: 'New application', to: `${sisPath('applications')}/new`, icon: icon(Plus) }] : []),
        ...(sis.can('students', 'create_direct') ? [{ label: 'Register student', to: `${sisPath('students')}/new`, icon: icon(Users) }] : []),
        ...(sis.codes.some(c => ['school.attendance.take', 'school.attendance.take_any'].includes(c)) ? [{ label: 'Take attendance', to: '/school/attendance', icon: icon(CalendarCheck) }] : []),
        ...(sis.can('marks', 'view') ? [{ label: 'Enter marks', to: '/school/marks', icon: icon(ClipboardCheck) }] : []),
        ...(sis.can('timetable-versions', 'view') ? [{ label: 'View timetable', to: '/school/timetable', icon: icon(CalendarDays) }] : []),
    ];
    return <PageLayout title="School dashboard" description="Enrollment, teaching and academic operations across your accessible campuses." breadcrumbs={['School', 'Dashboard']}
        actions={<div className="flex flex-wrap items-center gap-2">
            {campuses.length > 2 && <Select value={branch || '__all__'} onValueChange={v => setBranch(v === '__all__' ? '' : v)}>
                <SelectTrigger aria-label="Campus" className="h-9 w-[200px]"><Building2 className="mr-2 h-3.5 w-3.5 text-muted-foreground"/><SelectValue placeholder="All campuses"/></SelectTrigger>
                <SelectContent>{campuses.map(c => <SelectItem key={c.value || '__all__'} value={c.value || '__all__'}>{c.label}</SelectItem>)}</SelectContent>
            </Select>}
            {can('profile', 'view') && <Button asChild size="sm" variant="outline"><Link to="/school/settings"><Settings className="mr-2 h-4 w-4"/>School profile</Link></Button>}
        </div>}>
        {sis.error && <ErrorBanner message={sis.error} onRetry={sis.load} retryLabel="Retry permissions"/>}
        {!loading && data.failed.length > 0 && <ErrorBanner message={`Some dashboard data could not load: ${data.failed.join(', ')}.`} onRetry={() => setAttempt(v => v + 1)}/>}
        <SchoolDashboardView data={data} loading={loading} quickLinks={quickLinks}/>
    </PageLayout>;
}
