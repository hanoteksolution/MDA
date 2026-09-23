import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/layout/PageLayout';
import { ContentSection } from '@/components/layout/ContentSection';
import { schoolBreadcrumbs } from '@/navigation/schoolNavigation';
import { ErrorBanner } from '../components/SchoolUi';
import { Button } from '@/components/ui/button';
import { appDialog } from '@/components/feedback/AppDialog';
import { sisApi, type Field, type Roster, type Values } from './api';
import { Fields, inputClass } from './Fields';
import { path } from './config';
import { useSisPermissions } from './store';
import { ATTENDANCE_STATUSES, attendancePayload, markAll, slotReady, tally, toMarks, unmarked, type Mark } from './academics';
const rel = (name: string, label: string, lookup: string, sis = false, required = false): Field => ({name, label, kind:'relation', lookup, sis, required});
const fields: Field[] = [rel('branch_id','Campus','campuses',false,true), rel('school_class_id','Class','classes',false,true), {...rel('section_id','Section','sections'),nullable:true}, {name:'date',label:'Date',kind:'date',required:true},
 {name:'mode',label:'Attendance type',kind:'select',required:true,choices:[{value:'daily',label:'Daily'},{value:'period',label:'Period'}]}, {...rel('period_id','Period','periods',true),nullable:true}, {...rel('subject_offering_id','Subject','subject-offerings'),nullable:true}];
export function AttendancePage() {
 const permissions = useSisPermissions();
 const [slot, setSlot] = useState<Values>({date:new Date().toLocaleDateString('en-CA'), mode:'daily'});
 const [roster, setRoster] = useState<Roster>(); const [marks, setMarks] = useState<Mark[]>([]);
 const [error, setError] = useState(''); const [notice, setNotice] = useState(''); const [busy, setBusy] = useState(false); const lock = useRef(false);
 const shown = fields.filter(f => slot.mode === 'period' || !['period_id','subject_offering_id'].includes(f.name));
 const params = () => Object.fromEntries(Object.entries(attendancePayload(slot, [], false)).filter(([k]) => !['records','submit'].includes(k))) as Record<string, string>;
 const run = async (work: () => Promise<void>) => { if (lock.current) return; lock.current = true; setBusy(true); setError(''); setNotice(''); try { await work(); } catch (e) { setError(e instanceof Error ? e.message : 'Request failed.'); } finally { lock.current = false; setBusy(false); } };
 const load = () => run(async () => { const r = (await sisApi.roster(params())).data; setRoster(r); setMarks(toMarks(r.students)); });
 const save = (submit: boolean) => run(async () => {
  if (submit && !await appDialog.confirm('Submit attendance? It is locked afterwards and changes need an approved correction.', {title:'Submit attendance', confirmLabel:'Submit', tone:'default'})) return;
  const session = (await sisApi.take(attendancePayload(slot, marks, submit))).data;
  const r = (await sisApi.roster(params())).data; setRoster(r); setMarks(toMarks(r.students)); setNotice(submit ? 'Attendance submitted and locked.' : 'Attendance saved as a draft.'); void session;
 });
 const submitted = roster?.session?.status === 'submitted'; const canTake = permissions.codes.includes('school.attendance.take') || permissions.codes.includes('school.attendance.take_any');
 const totals = tally(marks);
 return <PageLayout title="Attendance" description="Take daily or period attendance for a class. Submitted registers are locked; changes need an approved correction." breadcrumbs={schoolBreadcrumbs('/school/attendance','Attendance')}><ContentSection>{permissions.error&&<ErrorBanner message={permissions.error} onRetry={permissions.load} retryLabel="Retry permissions"/>}
  <form className="mb-6 space-y-4" onSubmit={e => { e.preventDefault(); void load(); }}>
   <Fields fields={shown} values={slot} change={(k, v) => { setRoster(undefined); setMarks([]); setSlot(p => ({...p, [k]: v, ...(k==='school_class_id' ? {section_id:''} : {}), ...(k==='branch_id' ? {school_class_id:'',section_id:'',period_id:''} : {})})); }}/>
   <Button type="submit" disabled={busy || !slotReady(slot)}>Load class list</Button></form>
  {error&&<ErrorBanner message={error}/>}{notice && <p role="status" className="mb-4">{notice}</p>}
  {roster && (!marks.length ? <p>No students are enrolled in this class on that date.</p> : <section aria-label="Class attendance">
   <p className="mb-3 text-sm">{submitted ? 'Submitted and locked. ' : ''}{ATTENDANCE_STATUSES.map(s => `${s.replace('_',' ')}: ${totals[s]}`).join(' · ')} · Unmarked: {unmarked(marks)}</p>
   {!submitted && canTake && <div className="mb-3 flex gap-2"><Button variant="outline" type="button" onClick={() => setMarks(markAll(marks, 'present'))}>Mark all present</Button></div>}
   <div className="overflow-x-auto rounded-xl border"><table className="w-full text-left text-sm"><thead className="bg-muted/40 text-[11px] uppercase tracking-wide text-muted-foreground"><tr><th className="p-3">Roll</th><th className="p-3">Student</th><th className="p-3">Status</th><th className="p-3">Remarks</th></tr></thead><tbody>{marks.map((m, i) => <tr key={m.student_id} className="border-t"><td className="p-3">{m.roll_number || '—'}</td><td className="p-3">{m.student_name}</td>
    <td className="p-3"><label className="sr-only" htmlFor={`st-${i}`}>Status for {m.student_name}</label><select id={`st-${i}`} className={inputClass} disabled={submitted || !canTake} value={m.status} onChange={e => setMarks(marks.map((x, j) => j === i ? {...x, status: e.target.value} : x))}><option value="">Unmarked</option>{ATTENDANCE_STATUSES.map(s => <option key={s} value={s}>{s.replace('_',' ')}</option>)}</select></td>
    <td className="p-3"><label className="sr-only" htmlFor={`rm-${i}`}>Remarks for {m.student_name}</label><input id={`rm-${i}`} className={inputClass} maxLength={255} disabled={submitted || !canTake} value={m.remarks} onChange={e => setMarks(marks.map((x, j) => j === i ? {...x, remarks: e.target.value} : x))}/></td></tr>)}</tbody></table></div>
   {!submitted && canTake && <div className="mt-4 flex gap-3"><Button disabled={busy || !marks.some(m => m.status)} onClick={() => void save(false)}>Save draft</Button><Button disabled={busy || unmarked(marks) > 0} onClick={() => void save(true)}>Submit attendance</Button></div>}
   {submitted && <p className="mt-4 text-sm">To fix a mistake, open the <Link className="text-primary underline" to={`${path('attendance-records')}?session_id=${roster.session?.id}`}>attendance records</Link> and request a correction.</p>}
  </section>)}
 </ContentSection></PageLayout>;
}
