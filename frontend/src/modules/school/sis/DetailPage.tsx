import { ReportCard } from './ReportCard';
import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { Pencil, Archive, RotateCcw, Download, Printer, ChevronRight } from 'lucide-react';
import { PageLayout } from '@/components/layout/PageLayout';
import { ContentSection } from '@/components/layout/ContentSection';
import { LoadingState } from '@/components/layout/LoadingState';
import { Button } from '@/components/ui/button';
import { appDialog } from '@/components/feedback/AppDialog';
import { schoolBreadcrumbs } from '@/navigation/schoolNavigation';
import { sisApi, download, type Row } from './api';
import { resources, path, label, text } from './config';
import { useSisPermissions } from './store';
import { Actions } from './Actions';
import { singular, description, immutable, editable } from './meta';
import { commands } from './workflows';
import { DetailGrid, ErrorBanner, PermissionDenied, SchoolStatusBadge } from '../components/SchoolUi';

const children:Record<string,string[]>={students:['enrollments','transitions','student-guardians','student-documents','emergency-contacts','notes'],applicants:['applications','applicant-guardians'],applications:['applicant-documents','assessments','interviews','decisions'],families:['students','applicants'],guardians:['student-guardians','applicant-guardians'],employees:['staff-profiles'],'staff-profiles':['teacher-assignments','timetable-entries'],'timetable-versions':['timetable-entries'],'attendance-sessions':['attendance-records'],'attendance-records':['attendance-corrections']};
Object.assign(children,{exams:['academic-assessments','result-publications'],'academic-assessments':['marks','exam-schedules'],assignments:['submissions'],'result-publications':['report-cards','promotion-batches'],'promotion-batches':['promotion-items']});
const parentKey:Record<string,string>={students:'student_id',applications:'application_id',applicants:'applicant_id',families:'family_id',employees:'employee_id','staff-profiles':'staff_id','timetable-versions':'version_id','attendance-sessions':'session_id','attendance-records':'record_id'};
Object.assign(parentKey,{exams:'exam_id','academic-assessments':'assessment_id',assignments:'assignment_id','result-publications':'publication_id','promotion-batches':'batch_id'});
Object.assign(children,{'fee-structures':['fee-lines'],'fee-batches':['fee-invoices'],'billing-invoices':['billing-lines','billing-allocations','billing-credits'],'billing-receipts':['billing-allocations','billing-refunds']});
Object.assign(parentKey,{'fee-structures':'structure_id','fee-batches':'batch_id','billing-invoices':'invoice_id','billing-receipts':'receipt_id'});

export const relatedLinks = (resource: string, id: string, can: (resource: string) => boolean) =>
 (children[resource] || []).filter(can).map(child => ({ title: resources[child].title, to: `${path(child)}?${parentKey[resource] || 'guardian_id'}=${id}` }));

const HIDDEN = new Set(['id', 'name', 'status', 'deleted_at', 'deleted_by', 'snapshot', 'fingerprint']);
export const detailFields = (resource: string, row: Row) => Object.entries(row)
 // Structured payloads (snapshots, report data) have dedicated views; ids resolve to *_name fields.
 .filter(([k, v]) => !HIDDEN.has(k) && !k.endsWith('_id') && !k.endsWith('_url') && (v === null || typeof v !== 'object') && !(resource === 'report-cards' && k === 'data'))
 .map(([k, v]) => ({ label: label(k), value: k.endsWith('status') ? <SchoolStatusBadge status={v}/> : text(v) }));

export function SisDetailPage() {
 const {resource='students',id=''}=useParams();const [params]=useSearchParams();const archived=params.get('archived')==='true';const config=resources[resource];const location=useLocation();const navigate=useNavigate();
 const permissions=useSisPermissions();const [row,setRow]=useState<Row>();const [error,setError]=useState('');const [loading,setLoading]=useState(true);const [retry,setRetry]=useState(0);
 const denied=permissions.loaded&&!permissions.error&&Boolean(config)&&!permissions.can(resource,'view');
 useEffect(()=>{let active=true;setLoading(true);setError('');setRow(undefined);if(denied){setLoading(false);return;}sisApi.detail(resource,id,archived).then(r=>{if(active)setRow(r.data);}).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[resource,id,archived,retry,denied]);
 const title=singular(resource);
 const archive=async()=>{const verb=archived?'Restore':'Archive';if(!await appDialog.confirm(`${verb} ${row?.name||title.toLowerCase()}?`,{title:`${verb} ${title.toLowerCase()}`,confirmLabel:verb,tone:archived?'default':'danger'}))return;try{await sisApi.action(resource,id,archived?'restore':'archive');navigate(path(resource));}catch(e){setError(e instanceof Error?e.message:'Action failed.');}};
 const fail=(e:Error)=>setError(e.message);
 const headerActions=row&&<div className="flex flex-wrap gap-2">
  {resource==='billing-receipts'&&<Button size="sm" variant="outline" onClick={()=>download(`billing-receipts/${id}/print/`,'receipt.html',true).catch(fail)}><Printer className="mr-2 h-4 w-4"/>Print receipt</Button>}
  {resource==='report-cards'&&<Button size="sm" variant="outline" onClick={()=>download(`report-cards/${id}/print/`,'report-card.html',true).catch(fail)}><Printer className="mr-2 h-4 w-4"/>Open printable report / Save as PDF</Button>}
  {Boolean(row.file_id||row.photo_id)&&<Button size="sm" variant="outline" onClick={()=>download(`files/${row.file_id||row.photo_id}/?download=true`,'school-document').catch(fail)}><Download className="mr-2 h-4 w-4"/>Download attachment</Button>}
  {!immutable(resource)&&permissions.can(resource,archived?'restore':'archive')&&<Button size="sm" variant="outline" onClick={()=>void archive()}>{archived?<RotateCcw className="mr-2 h-4 w-4"/>:<Archive className="mr-2 h-4 w-4"/>}{archived?'Restore':'Archive'}</Button>}
  {!archived&&editable(resource)&&permissions.can(resource,'update')&&<Button size="sm" asChild><Link to={`${path(resource)}/${id}/edit`}><Pencil className="mr-2 h-4 w-4"/>Edit</Link></Button>}
 </div>;
 const related=row?relatedLinks(resource,id,child=>permissions.can(child,'view')):[];
 const workflow=row&&!archived&&commands(resource,row).some(c=>permissions.codes.includes(`school.${c.permission}`));
 const shortcuts=row?[
  ...(resource==='academic-assessments'&&permissions.can('marks','view')?[{title:'Enter marks',to:`/school/marks?assessment=${id}`}]:[]),
  ...(resource==='applications'&&row.student_id?[{title:'Open enrolled student',to:`${path('students')}/${row.student_id}`}]:[]),
 ]:[];
 return <PageLayout title={row?.name||(loading?`Loading ${title.toLowerCase()}…`:title)} description={description(resource)} breadcrumbs={schoolBreadcrumbs(location.pathname,config?.title||'Record',row?.name||'Details')} backTo={config?path(resource):'/school'} backLabel={config?`Back to ${config.title.toLowerCase()}`:'Back'} actions={headerActions||undefined}>
  {permissions.error&&<ErrorBanner message={permissions.error} onRetry={permissions.load} retryLabel="Retry permissions"/>}
  {error&&<ErrorBanner message={error} onRetry={()=>setRetry(v=>v+1)}/>}
  {denied?<ContentSection><PermissionDenied message={`Your role cannot view ${config?.title.toLowerCase()}.`}/></ContentSection>:loading?<LoadingState variant="page" label={`Loading ${title.toLowerCase()}`}/>:row&&<>
   <div className="flex flex-wrap items-center gap-3">{'status' in row&&<SchoolStatusBadge status={row.status}/>}{archived&&<SchoolStatusBadge status="archived"/>}{Boolean(row.branch_name)&&<span className="text-sm text-muted-foreground">{String(row.branch_name)}</span>}</div>
   {workflow&&<ContentSection title="Workflow" description="Actions available for the current status and your role."><Actions resource={resource} row={row} done={()=>setRetry(v=>v+1)}/></ContentSection>}
   {resource==='report-cards'&&<ReportCard row={row}/>}
   <ContentSection title="Details"><DetailGrid items={detailFields(resource,row)}/></ContentSection>
   {(related.length>0||shortcuts.length>0)&&<ContentSection title="Related records"><nav aria-label="Related records" className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{[...shortcuts,...related].map(link=><Link key={link.to} to={link.to} className="flex items-center justify-between rounded-xl border px-4 py-3 text-sm font-medium transition-colors hover:border-primary/40 hover:bg-muted/40">{link.title}<ChevronRight className="h-4 w-4 text-muted-foreground" aria-hidden/></Link>)}</nav></ContentSection>}
  </>}
 </PageLayout>;
}
