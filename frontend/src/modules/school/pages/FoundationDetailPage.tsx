import { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { Pencil } from 'lucide-react';
import { ContentSection } from '@/components/layout/ContentSection';
import { LoadingState } from '@/components/layout/LoadingState';
import { schoolBreadcrumbs } from '@/navigation/schoolNavigation';
import { DetailGrid, ErrorBanner, SchoolStatusBadge } from '../components/SchoolUi';
import { PageLayout } from '@/components/layout/PageLayout';
import { Button } from '@/components/ui/button';
import { appDialog } from '@/components/feedback/AppDialog';
import { schoolApi } from '@/services/api/school';
import { resources, schoolPath, type SchoolRecord, lifecycleActions } from '../foundation';
import { useCapabilities } from '../hooks/useFoundation';
import { RelatedRecords } from '../components/RelatedRecords';
export function FoundationDetailPage() {
    const { resource = 'academic-years', id = '' } = useParams();
    const config = resources[resource];
    const [query] = useSearchParams();
    const navigate = useNavigate();
    const location = useLocation();
    const { can, error: permissionError, retry: retryPermissions } = useCapabilities();
    const [row, setRow] = useState<SchoolRecord>();
    const [error, setError] = useState('');
    const [tab, setTab] = useState('Overview');
    const [retry, setRetry] = useState(0);
    useEffect(() => { let current = true; setRow(undefined); setError(''); schoolApi.detail(resource, id, query.get('archived') === 'true').then(r => { if (current)
        setRow(r.data); }).catch(e => { if (current)
        setError(e.message); }); return () => { current = false; }; }, [resource, id, query, retry]);
    if (!config)
        return <PageLayout title="School"><p>Record type not found.</p></PageLayout>;
    const action = async (a: string) => { if (!await appDialog.confirm(`${a} ${row?.name || config.singular}?`, { title: `${a} ${config.singular}`, confirmLabel: a }))
        return; try {
        await schoolApi.action(resource, id, a);
        navigate(schoolPath(resource));
    }
    catch (e) {
        setError(e instanceof Error ? e.message : 'Action failed.');
    } };
    const tabs = ['Overview', ...(resource === 'classes' ? ['Sections', 'Subjects'] : []), 'Activity'];
    return <PageLayout title={String(row?.name || config.singular)} description={config.description} breadcrumbs={schoolBreadcrumbs(location.pathname, config.title, String(row?.name || 'Details'))} backTo={schoolPath(resource)} backLabel={`Back to ${config.title.toLowerCase()}`} actions={<div className="flex gap-2">{row && !row.deleted_at && row.status !== 'closed' && row.is_active !== false && can(resource, 'update') && <Button asChild size="sm"><Link to={`${schoolPath(resource)}/${id}/edit`}><Pencil className="mr-2 h-4 w-4"/>Edit</Link></Button>}</div>}>
  {permissionError && <ErrorBanner message={permissionError} onRetry={retryPermissions} retryLabel="Retry permissions"/>}
  {error && <ErrorBanner message={error} onRetry={() => setRetry(v => v + 1)}/>}
  {!row && !error && <LoadingState variant="page" label="Loading record"/>}
  {row && <><div className="flex items-center gap-3"><SchoolStatusBadge status={row.deleted_at ? 'archived' : row.is_current ? 'current' : row.status ?? (row.is_active === false ? 'inactive' : 'active')}/><span className="text-sm text-muted-foreground">{String(row.branch_name || 'School-wide catalog')}</span></div>
   <div className="flex flex-wrap gap-2 border-b pb-2" role="tablist" aria-label="Record information">{tabs.map(t => <Button key={t} role="tab" aria-selected={tab === t} variant={tab === t ? 'secondary' : 'ghost'} onClick={() => setTab(t)}>{t}</Button>)}</div>
   {tab === 'Overview' && <ContentSection title="Details"><DetailGrid items={config.fields.map(f => ({ label: f.label, value: <>{typeof row[f.key] === 'boolean' ? (row[f.key] ? 'Yes' : 'No') : String(row[f.key.replace('_id', '_name')] ?? row[f.key] ?? '—')}{row[f.key.replace('_id', '_active')] === false && <span className="ml-2 text-destructive">Inactive reference</span>}</> }))}/></ContentSection>}
   {tab === 'Sections' && <RelatedRecords resource="sections" params={{ school_class_id: id }}/>}
   {tab === 'Subjects' && <RelatedRecords resource="subject-offerings" params={{ school_class_id: id }}/>}
   {tab === 'Activity' && <RelatedRecords resource={`${resource}/${id}/activity`} params={{ archived: query.get('archived') || 'false' }}/>}
   <div className="flex flex-wrap gap-2">{lifecycleActions(config, row, a => can(resource, a)).map(a => <Button key={a} variant="outline" onClick={() => void action(a)}>{a === 'activate' && resource === 'academic-years' ? 'Make current' : a[0].toUpperCase() + a.slice(1)}</Button>)}</div>
  </>}
 </PageLayout>;
}
