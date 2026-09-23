import { payload } from './payload';
import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { ContentSection } from '@/components/layout/ContentSection';
import { LoadingState } from '@/components/layout/LoadingState';
import { FormSection } from '@/components/forms/FormField';
import { schoolBreadcrumbs } from '@/navigation/schoolNavigation';
import { singular, description } from './meta';
import { ErrorBanner, PermissionDenied } from '../components/SchoolUi';
import { PageLayout } from '@/components/layout/PageLayout';
import { Button } from '@/components/ui/button';
import { appDialog } from '@/components/feedback/AppDialog';
import { ApiClientError } from '@/services/api/http';
import { useUnsavedChanges } from '../hooks/useUnsavedChanges';
import { sisApi, type Field, type Values } from './api';
import { resources, path, label } from './config';
import { Fields, inputClass } from './Fields';
import { useSisPermissions } from './store';
export function SisFormPage() {
 const {resource='students',id}=useParams();const [params]=useSearchParams();const config=resources[resource];const navigate=useNavigate();const location=useLocation();const permissions=useSisPermissions();
 const [fields,setFields]=useState<Field[]>([]);const [placementFields,setPlacementFields]=useState<Field[]>([]);const [guardianFields,setGuardianFields]=useState<Field[]>([]);
 const [values,setValues]=useState<Values>({});const [placement,setPlacement]=useState<Values>({});const [guardian,setGuardian]=useState<Values>({});const [addGuardian,setAddGuardian]=useState(false);const [reason,setReason]=useState('');
 const [error,setError]=useState('');const [errors,setErrors]=useState<Record<string,string[]>>({});const [loading,setLoading]=useState(true);const [saving,setSaving]=useState(false);const busy=useRef(false);const [dirty,setDirty]=useState(false);const [retry,setRetry]=useState(0);
 useUnsavedChanges(dirty);const direct=resource==='students'&&!id;
 useEffect(()=>{let active=true;setLoading(true);setError('');setDirty(false);
 Promise.all([sisApi.schema(resource),id?sisApi.detail(resource,id):Promise.resolve(null),direct?sisApi.schema('enrollments'):Promise.resolve(null),direct?sisApi.schema('student-guardians'):Promise.resolve(null)]).then(([schema,row,placementSchema,guardianSchema])=>{
 if(!active)return;let fs=schema.data;if(id&&resource==='students')fs=fs.filter(f=>!['branch_id','admission_date'].includes(f.name));if(id&&resource==='enrollments')fs=fs.filter(f=>['roll_number','notes'].includes(f.name));
 setFields(fs);setValues(row?.data||{...Object.fromEntries(fs.map(f=>[f.name,f.default??''])),...Object.fromEntries(params)});
 setPlacementFields((placementSchema?.data||[]).filter(f=>!['student_id','branch_id'].includes(f.name)));setGuardianFields((guardianSchema?.data||[]).filter(f=>f.name!=='student_id'));
 }).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[resource,id,retry]);
 useEffect(()=>{
 const parents: Record<string,string>={student_id:'students',applicant_id:'applicants',application_id:'applications',version_id:'timetable-versions',staff_id:'staff-profiles'};
 const entry=Object.entries(parents).find(([key])=>values[key]);if(!entry||id||direct)return;
 let active=true;sisApi.detail(entry[1],String(values[entry[0]])).then(r=>{if(active)setValues(v=>({...v,branch_id:r.data.branch_id}));}).catch(e=>{if(active)setError(e.message);});return()=>{active=false;};
 },[values.student_id,values.applicant_id,values.application_id,id,direct]);
 const change=(key:string,value:unknown)=>{setDirty(true);setValues(v=>({...v,[key]:value}));};
 const submit=async()=>{if(busy.current)return;busy.current=true;setSaving(true);setError('');setErrors({});try{
 const data=payload(fields,values);
 if(direct&&permissions.can('students','view')){const matches=(await sisApi.duplicates(data)).data;if(matches.length&&!await appDialog.confirm(`Possible existing students: ${matches.map(m=>m.name).join(', ')}. Create a separate student identity?`,{title:'Possible duplicate student',confirmLabel:'Create separate student',tone:'default'}))return;}
 const result=await sisApi.save(resource,direct?{student:data,placement:{...payload(placementFields,placement),branch_id:values.branch_id},guardians:addGuardian?[payload(guardianFields,guardian)]:[],reason}:data,id);
 setDirty(false);navigate(`${path(resource)}/${result.data.id}`);
 }catch(e){if(e instanceof ApiClientError)setErrors(e.fieldErrors);setError(e instanceof Error?e.message:'Could not save.');}finally{busy.current=false;setSaving(false);}};
 const noun=singular(resource).toLowerCase();
 const back=id?`${path(resource)}/${id}`:path(resource);
 return <PageLayout title={`${id?'Edit':'New'} ${noun}`} description={description(resource)} breadcrumbs={schoolBreadcrumbs(location.pathname,config?.title||'Record',id?'Edit':'New')} backTo={back} backLabel="Back">
 {permissions.error&&<ErrorBanner message={permissions.error} onRetry={permissions.load} retryLabel="Retry permissions"/>}
 {error&&<div className="space-y-2"><ErrorBanner message={error} onRetry={Object.keys(errors).length?undefined:()=>setRetry(v=>v+1)} retryLabel="Reload"/>{Object.keys(errors).length>0&&<ul className="list-disc pl-6 text-sm text-destructive">{Object.entries(errors).map(([k,v])=><li key={k}>{label(k)}: {v.join(' ')}</li>)}</ul>}</div>}
 {loading?<LoadingState variant="rows" rows={6} label={`Loading ${noun} form`}/>:!permissions.can(resource,id?'update':'create')?<ContentSection><PermissionDenied message={`Your role cannot ${id?'edit':'create'} ${config?.title.toLowerCase()||'records'}.`}/></ContentSection>:<form className="space-y-5" onSubmit={e=>{e.preventDefault();void submit();}}>
 <FormSection title={direct?'Student identity':'Details'}><Fields fields={fields} values={values} change={change} errors={errors} editing={Boolean(id)} resource={resource}/></FormSection>
 {direct&&<><FormSection title="Initial enrollment" description="Class and section placement for the current academic year."><Fields fields={placementFields} values={{...placement,branch_id:values.branch_id}} change={(k,v)=>{setDirty(true);setPlacement(p=>({...p,[k]:v}));}}/></FormSection>
 <FormSection title="Guardian"><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={addGuardian} onChange={e=>{setDirty(true);setAddGuardian(e.target.checked);}}/>Link an existing guardian (required unless school policy allows otherwise)</label>
 {addGuardian&&<div className="mt-4"><Fields fields={guardianFields} values={guardian} change={(k,v)=>{setDirty(true);setGuardian(p=>({...p,[k]:v}));}}/></div>}</FormSection>
 <FormSection title="Registration reason"><label className="block text-sm font-medium" htmlFor="direct-reason">Reason for direct registration *</label><textarea id="direct-reason" required className={`${inputClass} mt-1`} value={reason} onChange={e=>{setDirty(true);setReason(e.target.value);}}/></FormSection></>}
 <div className="sticky bottom-0 z-10 flex flex-wrap justify-end gap-3 rounded-xl border bg-card p-4 shadow-sm"><Button asChild variant="outline" type="button"><Link to={back}>Cancel</Link></Button><Button type="submit" loading={saving} disabled={saving||Boolean(permissions.error)||(direct&&!permissions.can(resource,'create_direct'))}>Save {noun}</Button></div>
 </form>}</PageLayout>;
}
