import { useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import { Plus } from 'lucide-react';
import type { FilterConfig } from '@/components/data/FilterBar';
import { schoolBreadcrumbs } from '@/navigation/schoolNavigation';
import { ErrorBanner, PermissionDenied, SchoolStatusBadge } from '../components/SchoolUi';
import { useLookupGroups } from '../hooks/useLookupOptions';
import { PageLayout } from '@/components/layout/PageLayout';
import { DataTable, type Column } from '@/components/data/DataTable';
import { Button } from '@/components/ui/button';
import { appDialog } from '@/components/feedback/AppDialog';
import { schoolApi, type SchoolPageData } from '@/services/api/school';
import { resources, schoolPath, type SchoolRecord } from '../foundation';
import { useCapabilities, useDebounced } from '../hooks/useFoundation';
import { ContentSection } from '@/components/layout/ContentSection';
import { RowActions } from '../components/RowActions';
const plural = (word: string) => word.endsWith('s') ? `${word}es` : word.endsWith('y') ? `${word.slice(0, -1)}ies` : `${word}s`;
export function FoundationListPage({ resource: fixed }: {
    resource?: string;
}) {
    const params = useParams();
    const resource = fixed || params.resource || 'academic-years';
    const config = resources[resource];
    const { can, loaded: capabilitiesLoaded, error: permissionError, retry: retryPermissions } = useCapabilities();
    const location = useLocation();
    const [data, setData] = useState<SchoolPageData>();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [search, setSearch] = useState('');
    const debounced = useDebounced(search);
    const [page, setPage] = useState(1);
    const [size, setSize] = useState(25);
    const [ordering, setOrdering] = useState('name');
    const [archived, setArchived] = useState(false);
    const [status, setStatus] = useState('');
    const [filters, setFilters] = useState<Record<string, string>>({});
    const [reload, setReload] = useState(0);
    const [hidden, setHidden] = useState<string[]>([]);
    const filterKey = JSON.stringify(filters);
    const relationFilters = (config?.fields || []).filter(f => f.type === 'relation' && !['teacher_id', 'user_id', 'company_id'].includes(f.key));
    const lookups = useLookupGroups(relationFilters.map(f => ({ resource: f.resource!, allLabel: `All ${plural(f.label.toLowerCase())}`, params: f.key === 'branch_id' ? {} : { branch_id: filters.branch_id || undefined, academic_year_id: f.key === 'term_id' ? filters.academic_year_id || undefined : undefined, school_class_id: f.key === 'section_id' ? filters.school_class_id || undefined : undefined } })));
    useEffect(() => { setPage(1); }, [resource, debounced, size, ordering, status, archived, filterKey]);
    useEffect(() => { setFilters({}); setStatus(''); setSearch(''); setArchived(false); setData(undefined); setOrdering(resource === 'campus-access' ? '-created_at' : 'name'); }, [resource]);
    useEffect(() => { let active = true; if (!config)
        return; setLoading(true); setError(''); schoolApi.list(resource, { ...filters, search: debounced, page, page_size: size, ordering, status, archived }).then(r => { if (active)
        setData(r.data); }).catch(e => { if (active) {
        setError(e.message);
        setData(undefined);
    } }).finally(() => { if (active)
        setLoading(false); }); return () => { active = false; }; }, [resource, debounced, page, size, ordering, status, archived, filterKey, reload]);
    if (!config)
        return <PageLayout title="School"><p>Academic area not found.</p></PageLayout>;
    const action = async (row: SchoolRecord, name: string) => { if (!await appDialog.confirm(`${name[0].toUpperCase() + name.slice(1)} ${row.name || config.singular}?`, { title: `${name} ${config.singular}`, confirmLabel: name }))
        return; try {
        await schoolApi.action(resource, row.id, name);
        setReload(v => v + 1);
    }
    catch (e) {
        setError(e instanceof Error ? e.message : 'Action failed.');
    } };
    const textKeys = config.fields.filter(f => !['description', 'teacher_id', 'user_id'].includes(f.key) && f.type !== 'checkbox').slice(0, 6);
    const columns: Column<SchoolRecord>[] = [...textKeys.map(f => ({ key: f.key, header: f.label, cell: (r: SchoolRecord) => f.key === 'name' ? <Link className="font-medium text-primary hover:underline" to={`${schoolPath(resource)}/${r.id}${archived ? '?archived=true' : ''}`}>{String(r.name)}</Link> : String(r[f.key.replace('_id', '_name')] ?? r[f.key] ?? '—'), exportValue: (r: SchoolRecord) => String(r[f.key.replace('_id', '_name')] ?? r[f.key] ?? '') })), { key: 'state', header: 'Status', cell: r => <SchoolStatusBadge status={r.deleted_at ? 'archived' : r.is_current ? 'current' : r.status ?? (r.is_active === false ? 'inactive' : 'active')}/> }, { key: 'actions', header: '', cell: r => <RowActions resource={resource} row={r} can={a => can(resource, a)} onAction={a => void action(r, a)}/> }];
    const filterFields = relationFilters;
    const denied = !permissionError && capabilitiesLoaded && !can(resource, 'view');
    const toolbar: FilterConfig[] = [
        ...filterFields.map((f, i) => ({ key: f.key, label: f.label, value: filters[f.key] || '', onChange: (v: string) => setFilters(current => ({ ...current, [f.key]: v })), options: lookups[i] })),
        ...(resource !== 'campuses' && resource !== 'campus-access' ? [{ key: 'status', label: 'Status', value: status, onChange: setStatus, options: [{ value: '', label: 'All statuses' }, ...(config.period ? ['planning', 'active', 'closed'] : ['active', 'inactive']).map(s => ({ value: s, label: s[0].toUpperCase() + s.slice(1) }))] }] : []),
        { key: 'ordering', label: 'Sort', value: ordering, onChange: (v: string) => setOrdering(v || 'name'), options: (resource === 'campus-access' ? ['-created_at', 'created_at'] : ['name', '-name', 'code', '-created_at']).map(s => ({ value: s, label: ({ name: 'Name A–Z', '-name': 'Name Z–A', code: 'Code', '-created_at': 'Newest first', created_at: 'Oldest first' } as Record<string, string>)[s] })) },
    ];
    const toggles = <div className="flex flex-wrap items-center gap-2 text-sm">
        <label className="flex h-9 items-center gap-2 rounded-lg border px-3"><input type="checkbox" checked={archived} onChange={e => setArchived(e.target.checked)}/>Show archived</label>
        {resource === 'academic-years' && <label className="flex h-9 items-center gap-2 rounded-lg border px-3"><input type="checkbox" checked={filters.is_current === 'true'} onChange={e => setFilters({ ...filters, is_current: e.target.checked ? 'true' : '' })}/>Current years only</label>}
        <details className="relative"><summary className="flex h-9 cursor-pointer list-none items-center rounded-lg border px-3">Visible columns</summary><div className="absolute right-0 z-20 mt-1 w-52 rounded-xl border bg-popover p-3 shadow-lg">{textKeys.map(f => <label key={f.key} className="mt-1 flex gap-2 first:mt-0"><input type="checkbox" checked={!hidden.includes(f.key)} onChange={() => setHidden(hidden.includes(f.key) ? hidden.filter(k => k !== f.key) : [...hidden, f.key])}/>{f.label}</label>)}</div></details>
    </div>;
    return <PageLayout title={config.title} description={config.description} breadcrumbs={schoolBreadcrumbs(location.pathname, config.title)} actions={can(resource, 'create') ? <Button asChild size="sm"><Link to={`${schoolPath(resource)}/new`}><Plus className="mr-2 h-4 w-4"/>New {config.singular.toLowerCase()}</Link></Button> : undefined}>
  {(error || permissionError) && <ErrorBanner message={error || permissionError} onRetry={() => { setReload(v => v + 1); if (permissionError) retryPermissions(); }}/>}
  {denied ? <ContentSection><PermissionDenied message={`Your role cannot view ${config.title.toLowerCase()}.`}/></ContentSection> : <DataTable columns={columns.filter(c => !hidden.includes(c.key))} data={data?.results || []} loading={loading} page={page} pageSize={size} total={data?.count || 0} onPageChange={setPage} onPageSizeChange={setSize} searchValue={search} onSearchChange={setSearch} searchPlaceholder={`Search ${config.title.toLowerCase()}…`} filters={toolbar} actions={toggles} exportTitle={`${config.title} — page ${page}`} emptyMessage={error ? 'Records could not be loaded.' : `No ${config.title.toLowerCase()} match these filters.`}/>}
 </PageLayout>;
}
