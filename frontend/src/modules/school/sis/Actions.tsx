import { payload } from './payload';
import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { appDialog } from '@/components/feedback/AppDialog';
import { ErrorBanner } from '../components/SchoolUi';
import { sisApi, type Field, type Row, type Values } from './api';
import { Fields } from './Fields';
import { commands, commandPayload, type Command } from './workflows';
import { useSisStore } from './store';
export function Actions({resource,row,done}:{resource:string;row:Row;done:()=>void}) {
 const codes=useSisStore(s=>s.codes);const [command,setCommand]=useState<Command>();const [values,setValues]=useState<Values>({});const [placement,setPlacement]=useState<Values>({});const [fields,setFields]=useState<Field[]>([]);const [error,setError]=useState('');const [saving,setSaving]=useState(false);const busy=useRef(false);
 useEffect(()=>{if(!command?.placement)return;setFields([]);sisApi.schema('enrollments').then(r=>setFields(r.data.filter(f=>!['student_id','start_date','end_date'].includes(f.name)))).catch(e=>setError(e.message));},[command]);
 const submit=async()=>{if(busy.current||!command)return;if(!await appDialog.confirm(`${command.title}?`,{title:command.title,confirmLabel:command.title,tone:/withdraw|cancel|reject|reverse|suspend/i.test(command.action)?'danger':'default'}))return;busy.current=true;setSaving(true);setError('');try{await sisApi.action(resource,row.id,command.action,commandPayload(command,values,payload(fields,placement),row));setCommand(undefined);done();}catch(e){setError(e instanceof Error?e.message:'Action failed.');}finally{busy.current=false;setSaving(false);}};
 return <section className="space-y-4"><div className="flex flex-wrap gap-2">{commands(resource,row).filter(c=>codes.includes(`school.${c.permission}`)).map(c=><Button size="sm" variant={command?.action===c.action?'default':'outline'} key={c.action} onClick={()=>{setCommand(c);setValues({});setPlacement({branch_id:row.branch_id});setError('');}}>{c.title}</Button>)}</div>
 {command&&<form className="space-y-4 rounded-xl border bg-muted/20 p-5" aria-label={command.title} onSubmit={e=>{e.preventDefault();void submit();}}><h3 className="font-semibold">{command.title}</h3>{error&&<ErrorBanner message={error}/>}
 <Fields fields={command.fields} values={{branch_id:row.branch_id,...values}} change={(k,v)=>setValues(p=>({...p,[k]:v}))}/>
 {command.placement&&<Fields fields={fields} values={placement} change={(k,v)=>setPlacement(p=>({...p,[k]:v}))}/>}
 <div className="flex justify-end gap-2"><Button type="button" variant="outline" disabled={saving} onClick={()=>setCommand(undefined)}>Cancel</Button><Button disabled={saving||(command.placement&&!fields.length)}>{saving?'Saving…':'Confirm'}</Button></div></form>}
 </section>;
}
