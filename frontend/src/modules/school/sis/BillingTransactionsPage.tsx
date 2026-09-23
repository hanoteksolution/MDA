import { useRef,useState } from 'react';
import { Link } from 'react-router-dom';
import { PageLayout } from '@/components/layout/PageLayout';
import { ContentSection } from '@/components/layout/ContentSection';
import { schoolBreadcrumbs } from '@/navigation/schoolNavigation';
import { ErrorBanner, Denied } from '../components/SchoolUi';
import { Button } from '@/components/ui/button';
import { appDialog } from '@/components/feedback/AppDialog';
import { billingModes,billingError } from './billing';
import { useUnsavedChanges } from '../hooks/useUnsavedChanges';
import { Fields,inputClass } from './Fields';
import { useSisPermissions } from './store';
import { sisApi,type Row,type Values } from './api';
export function BillingTransactionsPage(){
 const permissions=useSisPermissions();const [mode,setMode]=useState<keyof typeof billingModes>('billing-receipts');const [values,setValues]=useState<Values>({date:new Date().toISOString().slice(0,10)});const [key,setKey]=useState(()=>crypto.randomUUID());const [saved,setSaved]=useState<Row>();const [busy,setBusy]=useState(false);const inFlight=useRef(false);const [error,setError]=useState('');const [dirty,setDirty]=useState(false);useUnsavedChanges(dirty&&!saved);
 async function submit(){if(inFlight.current)return;if(!await appDialog.confirm('Confirm this financial transaction and its ledger posting?',{title:'Post transaction',confirmLabel:'Post',tone:'default'}))return;inFlight.current=true;setBusy(true);setError('');try{setSaved((await sisApi.save(mode,{...values,idempotency_key:key})).data);setDirty(false);}catch(e){setError(billingError(e));}finally{inFlight.current=false;setBusy(false);}}
 function reset(next:keyof typeof billingModes=mode){setMode(next);setValues({date:new Date().toISOString().slice(0,10)});setKey(crypto.randomUUID());setSaved(undefined);setDirty(false);setError('');}
 const config=billingModes[mode];
 return <PageLayout title="Payments, allocations and adjustments" description="Record receipts, allocate advances to invoices, and issue approved credits or refunds." breadcrumbs={schoolBreadcrumbs('/school/finance/transactions','Payments, allocations and adjustments')}><ContentSection>{error&&<ErrorBanner message={error}/>}<div className="space-y-5"><p>A receipt records cash once. Allocate its available advance to one or more invoices using separate allocations. To refund paid fees, reverse the allocation, issue an approved credit where applicable, then refund the available funds.</p><label className="block">Transaction<select aria-label="Transaction" className={inputClass} value={mode} disabled={busy} onChange={e=>{if(!dirty||window.confirm('Discard the unsaved transaction?'))reset(e.target.value as keyof typeof billingModes);}}>{Object.entries(billingModes).filter(([,c])=>permissions.codes.includes(c.permission)).map(([k,c])=><option key={k} value={k}>{c.title}</option>)}</select></label>{permissions.codes.includes(config.permission)?<form className="space-y-4" onSubmit={e=>{e.preventDefault();void submit();}}><fieldset disabled={busy||Boolean(saved)}><Fields fields={config.fields} values={values} change={(k,v)=>{setValues(x=>({...x,[k]:v}));setDirty(true);}}/></fieldset>{!saved&&<Button disabled={busy}>{busy?'Posting…':'Post transaction'}</Button>}</form>:<Denied loaded={permissions.loaded} message="This transaction requires an authorized financial role."/>}{saved&&<section className="rounded-xl border p-4 space-y-4"><p role="status">Transaction posted.</p><Link className="text-primary underline" to={`/school/sis/${mode}/${saved.id}`}>View transaction and history</Link><Button variant="outline" onClick={()=>reset()}>New transaction</Button></section>}</div></ContentSection></PageLayout>;
}
