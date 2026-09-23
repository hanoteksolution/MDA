import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/layout/PageLayout';
import { ContentSection } from '@/components/layout/ContentSection';
import { schoolBreadcrumbs } from '@/navigation/schoolNavigation';
import { ErrorBanner } from '../components/SchoolUi';
import { sisApi, type Page, type Row } from './api';
import { Fields } from './Fields';
import { path } from './config';
import { useSisPermissions } from './store';
import { WEEKDAYS, lessonLabel, timetableGrid } from './academics';
const versionField = [{name:'version_id',label:'Timetable',kind:'relation',lookup:'timetable-versions',sis:true,required:true}];
export function TimetablePage() {
 const permissions = useSisPermissions(); const [version, setVersion] = useState(''); const [detail, setDetail] = useState<Row>();
 const [periods, setPeriods] = useState<Row[]>([]); const [entries, setEntries] = useState<Page>(); const [error, setError] = useState(''); const [loading, setLoading] = useState(false); const [days, setDays] = useState(5);
 useEffect(() => { if (!version) return; let active = true; setLoading(true); setError(''); setEntries(undefined);
  sisApi.detail('timetable-versions', version).then(async v => { const [p, e] = await Promise.all([sisApi.list('periods', {branch_id:String(v.data.branch_id), status:'active', page_size:100}), sisApi.list('timetable-entries', {version_id:version, status:'active', page_size:100})]); if (active) { setDetail(v.data); setPeriods(p.data.results); setEntries(e.data); } })
   .catch(e => { if (active) setError(e.message); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; }; }, [version]);
 const grid = timetableGrid(periods, entries?.results || [], [1,2,3,4,5,6,7].slice(0, days));
 return <PageLayout title="Timetable" description="Weekly lesson grid for a timetable version." breadcrumbs={schoolBreadcrumbs('/school/timetable','Timetable')}><ContentSection>{permissions.error&&<ErrorBanner message={permissions.error} onRetry={permissions.load} retryLabel="Retry permissions"/>}
  <div className="mb-5 max-w-md"><Fields fields={versionField} values={{version_id:version}} change={(_, v) => { setVersion(String(v)); setDetail(undefined); }}/></div>
  {error&&<ErrorBanner message={error}/>}{loading && <p role="status">Loading…</p>}
  {detail && <><p className="mb-3 text-sm">{String(detail.name)} · {String(detail.status)} · from {String(detail.effective_from)}{permissions.can('timetable-entries','create') && detail.status === 'draft' && <> · <Link className="text-primary underline" to={`${path('timetable-entries')}/new?version_id=${detail.id}`}>Add lesson</Link></>} · <Link className="text-primary underline" to={`${path('timetable-versions')}/${detail.id}`}>Open version</Link>
   <label className="ml-4">Days <select className="ml-1 h-8 rounded-md border bg-background px-2" value={days} onChange={e => setDays(Number(e.target.value))}>{[5,6,7].map(d => <option key={d} value={d}>{d}</option>)}</select></label></p>
   {entries && entries.count > entries.results.length && <p role="alert">Showing the first {entries.results.length} of {entries.count} lessons; use the lessons list to filter.</p>}
   {!periods.length ? <p>No periods are defined for this campus.</p> : <div className="overflow-x-auto rounded-xl border"><table className="w-full text-left text-sm"><thead className="bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground"><tr><th className="p-3">Period</th>{WEEKDAYS.slice(0, days).map(d => <th key={d} className="p-3">{d}</th>)}</tr></thead>
    <tbody>{grid.map(row => <tr key={row.period.id} className="border-t align-top"><th scope="row" className="whitespace-nowrap p-3">{String(row.period.name)}<br/><span className="text-xs font-normal">{String(row.period.start_time).slice(0,5)}–{String(row.period.end_time).slice(0,5)}</span></th>
     {row.cells.map(cell => <td key={cell.weekday} className="p-3">{cell.entries.map(e => <Link key={e.id} className="mb-1 block rounded-lg border border-primary/20 bg-primary/5 px-2 py-1 text-xs font-medium text-primary hover:bg-primary/10" to={`${path('timetable-entries')}/${e.id}`}>{lessonLabel(e)}</Link>)}</td>)}</tr>)}</tbody></table></div>}</>}
 </ContentSection></PageLayout>;
}
