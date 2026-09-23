import { useState } from 'react';
import { RelationField } from '../components/RelationField';
import { upload, type Field, type Values } from './api';

export const inputClass = 'w-full rounded-lg border border-input bg-background px-3 py-2 text-sm';
export function Fields({fields, values, change, errors = {}, editing = false, resource = ''}: {
 fields: Field[]; values: Values; change: (key: string, value: unknown) => void; errors?: Record<string, string[]>; editing?: boolean; resource?: string;
}) {
 const [error, setError] = useState(''); const [uploading, setUploading] = useState(false);
 const branch = String(values.branch_id || '');
 return <div className="grid gap-5 md:grid-cols-2">{error && <p role="alert">{error}</p>}{fields.map(f => {
 const id = `sis-${f.name}`; const value = values[f.name] ?? f.default ?? '';
 const disabled = editing && ['branch_id','student_id','applicant_id','application_id','academic_year_id','school_class_id','guardian_id','employee_id','staff_id','version_id'].includes(f.name);
 const props = {id, required:f.required, disabled, 'aria-describedby':errors[f.name] ? `${id}-error` : undefined, 'aria-invalid':Boolean(errors[f.name])};
 let params: Record<string,string|undefined> = {};
 if (f.lookup !== 'campuses' && branch) params.branch_id = branch;
 if (f.lookup === 'sections') params.school_class_id = String(values.school_class_id || values.desired_class_id || '');
 if (f.lookup === 'terms') params.academic_year_id = String(values.academic_year_id || '');
 if (f.lookup === 'admissions-staff') params = {branch_id:branch, action: f.name === 'assessor_id' ? 'assess' : f.name === 'interviewer_id' ? 'interview' : 'review'};
 const lookup = f.lookup === 'admissions-staff' ? 'sis/staff' : f.sis ? `sis/${f.lookup}` : f.lookup || 'lookups/campuses';
 return <div key={f.name} className="space-y-1"><label htmlFor={id} className="text-sm font-medium">{f.label}{f.required ? ' *' : ''}</label>
 {f.kind === 'relation' ? <RelationField {...props} disabled={disabled || (f.lookup === 'admissions-staff' && !branch)} label={f.label} resource={lookup} params={params} value={String(value)} currentLabel={String(values[f.name.replace(/_id$/, '_name')] || '')} onChange={v=>change(f.name,v)} />
 : f.kind === 'checkbox' ? <input {...props} type="checkbox" checked={Boolean(value)} onChange={e=>change(f.name,e.target.checked)} />
 : f.kind === 'select' ? <select {...props} className={inputClass} value={String(value)} onChange={e=>change(f.name,e.target.value)}><option value="">Select…</option>{f.choices?.map(c=><option key={c.value} value={c.value}>{c.label}</option>)}</select>
 : f.kind === 'multiselect' ? <select {...props} multiple className={inputClass} value={Array.isArray(value) ? value as string[] : []} onChange={e=>change(f.name,Array.from(e.target.selectedOptions,o=>o.value))}>{['application/pdf','image/png','image/jpeg','image/webp'].map(v=><option key={v}>{v}</option>)}</select>
 : f.kind === 'file' ? <><input {...props} disabled={uploading || !branch} type="file" accept="application/pdf,image/png,image/jpeg,image/webp" onChange={async e=>{const file=e.target.files?.[0];if(!file)return;setUploading(true);setError('');try {const purpose=f.name==='photo_id' ? resource==='applicants'?'applicant_photo':'student_photo':resource==='applicant-documents'?'admission':'student';change(f.name,(await upload(file,branch,purpose)).id);}catch(e){setError(e instanceof Error?e.message:'Upload failed.');}finally{setUploading(false);}}}/><p className="text-xs text-muted-foreground">{uploading?'Uploading…':value?'File attached.':'Select a campus before uploading.'}</p></>
 : f.kind === 'textarea' ? <textarea {...props} className={inputClass} value={String(value)} onChange={e=>change(f.name,e.target.value)}/>
 : <input {...props} className={inputClass} type={f.kind} step={f.kind==='number'?'any':undefined} maxLength={f.max_length} value={String(value)} onChange={e=>change(f.name,e.target.value)}/>}
 {errors[f.name] && <p id={`${id}-error`} role="alert" className="text-sm text-destructive">{errors[f.name].join(' ')}</p>}
 </div>;
 })}</div>;
}
