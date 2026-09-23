import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ClipboardList, FileWarning, Hourglass, UserCheck, Plus } from 'lucide-react';
import { PageLayout } from '@/components/layout/PageLayout';
import { ContentSection } from '@/components/layout/ContentSection';
import { EmptyState } from '@/components/layout/EmptyState';
import { KpiCard, KpiGrid } from '@/components/data/KpiCard';
import { Button } from '@/components/ui/button';
import { schoolBreadcrumbs } from '@/navigation/schoolNavigation';
import { sisApi, type Row, type Values } from './api';
import { path, text } from './config';
import { useSisPermissions } from './store';
import { Denied, ErrorBanner, SchoolStatusBadge } from '../components/SchoolUi';

type Breakdown = { count: number; [key: string]: unknown }[];
const n = (value: unknown) => (typeof value === 'number' ? value.toLocaleString() : '—');

function RecordList({ rows, empty, render }: { rows: Row[]; empty: string; render: (row: Row) => React.ReactNode }) {
 return rows.length ? <ul className="divide-y">{rows.map(row => <li key={row.id} className="py-2.5">{render(row)}</li>)}</ul> : <EmptyState compact title={empty}/>;
}

function BreakdownList({ rows, field }: { rows: Breakdown; field: string }) {
 const max = Math.max(1, ...rows.map(r => r.count));
 return rows.length ? <ul className="space-y-2.5">{rows.map((r, i) => <li key={i} className="text-sm"><div className="flex justify-between gap-3"><span className="truncate">{String(r[field] ?? 'Unspecified')}</span><span className="font-medium tabular-nums">{r.count}</span></div><div className="mt-1 h-1.5 rounded-full bg-muted" aria-hidden><div className="h-1.5 rounded-full bg-primary" style={{ width: `${(100 * r.count) / max}%` }}/></div></li>)}</ul> : <EmptyState compact title="No applications yet."/>;
}

/** Admissions pipeline built only from `/school/sis/dashboard/` values. */
export function AdmissionsOverview({ data }: { data: Values }) {
 const recent = (data.recent_applications || []) as Row[];
 const missing = (data.missing_documents || []) as Row[];
 const interviews = (data.upcoming_interviews || []) as Row[];
 const open = ['new_applications', 'under_review', 'accepted', 'waitlisted'].reduce((sum, key) => sum + (Number(data[key]) || 0), 0);
 const app = (row: Row) => <Link className="flex items-center justify-between gap-3 text-sm" to={`${path('applications')}/${row.id}`}><span className="min-w-0"><span className="block truncate font-medium text-primary">{text(row.applicant_name || row.name)}</span><span className="block truncate text-xs text-muted-foreground">{[row.number, row.school_class_name, row.branch_name].filter(Boolean).map(text).join(' · ')}</span></span><SchoolStatusBadge status={row.status}/></Link>;
 return <>
  <KpiGrid columns={4}>
   <KpiCard index={0} title="Open applications" value={n(open)} icon={<ClipboardList className="h-5 w-5"/>}/>
   <KpiCard index={1} title="Under review" value={n(data.under_review)} icon={<Hourglass className="h-5 w-5"/>} accent="warning"/>
   <KpiCard index={2} title="Missing documents" value={n(data.pending_documents)} icon={<FileWarning className="h-5 w-5"/>} accent="warning"/>
   <KpiCard index={3} title="Enrolled" value={n(data.enrolled)} icon={<UserCheck className="h-5 w-5"/>} accent="success"/>
  </KpiGrid>
  <div className="grid gap-4 xl:grid-cols-3">
   <ContentSection title="Pipeline" index={1}><dl className="grid grid-cols-2 gap-4 text-sm">{([['Total', 'total_applications'], ['Conversion %', 'conversion_rate'], ['New', 'new_applications'], ['Under review', 'under_review'], ['Accepted', 'accepted'], ['Waitlisted', 'waitlisted'], ['Rejected', 'rejected'], ['Enrolled', 'enrolled'], ['Assessments scheduled', 'assessment_scheduled'], ['Interviews scheduled', 'interview_scheduled']] as const).filter(([, key]) => data[key] !== null && data[key] !== undefined).map(([title, key]) => <div key={key}><dt className="text-xs text-muted-foreground">{title}</dt><dd className="text-lg font-semibold tabular-nums">{n(data[key])}</dd></div>)}</dl></ContentSection>
   <div className="xl:col-span-2"><ContentSection title="Recent applications" index={2} action={<Button asChild size="sm" variant="ghost"><Link to={path('applications')}>View all</Link></Button>}><RecordList rows={recent} empty="No applications yet." render={app}/></ContentSection></div>
  </div>
  <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
   <ContentSection title="Missing documents" index={3} action={<Button asChild size="sm" variant="ghost"><Link to={`${path('applications')}?missing_documents=true`}>View all</Link></Button>}><RecordList rows={missing} empty="All required documents are verified." render={app}/></ContentSection>
   <ContentSection title="Upcoming interviews" index={4}><RecordList rows={interviews} empty="No interviews scheduled." render={row => <Link className="block text-sm" to={`${path('interviews')}/${row.id}`}><span className="font-medium text-primary">{text(row.name)}</span><span className="block text-xs text-muted-foreground">{text(row.date)} · {text(row.start_time)}{row.location ? ` · ${text(row.location)}` : ''}</span></Link>}/></ContentSection>
   <ContentSection title="Applications by class" index={5}><BreakdownList rows={(data.by_class || []) as Breakdown} field="school_class__name"/></ContentSection>
  </div>
 </>;
}

export function AdmissionsDashboardPage() {
 const permissions=useSisPermissions();const [data,setData]=useState<Values>();const [error,setError]=useState('');const [retry,setRetry]=useState(0);
 const allowed=permissions.can('applications','view');
 useEffect(()=>{setError('');let active=true;if(!allowed)return;sisApi.dashboard({}).then(r=>{if(active)setData(r.data);}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};},[retry,allowed]);
 return <PageLayout title="Admissions" description="Application pipeline, document follow-up and upcoming interviews across your accessible campuses." breadcrumbs={schoolBreadcrumbs('/school/admissions','Admissions')}
  actions={permissions.can('applications','create')?<Button asChild size="sm"><Link to={`${path('applications')}/new`}><Plus className="mr-2 h-4 w-4"/>New application</Link></Button>:undefined}>
  {permissions.error&&<ErrorBanner message={permissions.error} onRetry={permissions.load} retryLabel="Retry permissions"/>}
  {!allowed?<ContentSection><Denied loaded={permissions.loaded} message="Admissions access is not included in your role."/></ContentSection>
   :error?<ErrorBanner message={error} onRetry={()=>setRetry(v=>v+1)}/>
   :!data?<KpiGrid columns={4}>{[0,1,2,3].map(i=><KpiCard key={i} index={i} title="Loading" value="—" loading/>)}</KpiGrid>
   :<AdmissionsOverview data={data}/>}
 </PageLayout>;
}
