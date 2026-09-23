import { useEffect, useState } from 'react';
import { Link, useLocation, useParams, useSearchParams } from 'react-router-dom';
import { Plus, X } from 'lucide-react';
import { PageLayout } from '@/components/layout/PageLayout';
import { ContentSection } from '@/components/layout/ContentSection';
import { DataTable, type Column } from '@/components/data/DataTable';
import type { FilterConfig, FilterOption } from '@/components/data/FilterBar';
import { Button } from '@/components/ui/button';
import { appDialog } from '@/components/feedback/AppDialog';
import { schoolBreadcrumbs } from '@/navigation/schoolNavigation';
import { sisApi, download, type Page, type Row } from './api';
import { resources, path, label, text } from './config';
import { useSisPermissions } from './store';
import { singular, description, immutable, editable, exportable, classFilter, WORKFLOW_ENTRY } from './meta';
import { useDebounced } from '../hooks/useFoundation';
import { useLookupOptions } from '../hooks/useLookupOptions';
import { ErrorBanner, PermissionDenied, RecordMenu, SchoolStatusBadge, type MenuItem } from '../components/SchoolUi';

const STRUCTURAL = new Set(['branch_id', 'school_class_id', 'section_id', 'academic_year_id', 'status', 'search', 'ordering', 'page', 'page_size', 'archived']);

/** Filters that came from a parent record ("Enrollments of this student"). */
export function parentFilters(params: URLSearchParams): [string, string][] {
 return [...params].filter(([key, value]) => key.endsWith('_id') && !STRUCTURAL.has(key) && value);
}

export function listColumns(resource: string, archived: boolean, actions: (row: Row) => MenuItem[]): Column<Row>[] {
 const config = resources[resource];
 const detail = (row: Row) => `${path(resource)}/${row.id}${archived ? '?archived=true' : ''}`;
 const columns: Column<Row>[] = config.columns.map((column, i) => ({
  key: column,
  header: label(column),
  cell: (row: Row) => i === 0
   ? <Link className="font-medium text-primary hover:underline" to={detail(row)}>{column.endsWith('_id') ? row.name || text(row[column]) : text(row[column])}</Link>
   : column === 'status' || column.endsWith('_status') ? <SchoolStatusBadge status={row[column]}/> : text(row[column]),
  exportValue: (row: Row) => text(row[column]),
 }));
 columns.push({ key: 'actions', header: '', className: 'w-12 text-right', cell: row => <RecordMenu label={String(row.name || text(row[config.columns[0]]))} items={actions(row)}/> });
 return columns;
}

export function SisListPage() {
 const { resource = 'students' } = useParams(); const config = resources[resource]; const location = useLocation();
 const [params, setParams] = useSearchParams(); const permissions = useSisPermissions();
 const [data, setData] = useState<Page>(); const [error, setError] = useState(''); const [loading, setLoading] = useState(true); const [retry, setRetry] = useState(0);
 const [search, setSearch] = useState(params.get('search') || ''); const debounced = useDebounced(search);
 const [statuses, setStatuses] = useState<FilterOption[]>([]);
 const query = params.toString(); const archived = params.get('archived') === 'true';
 const denied = permissions.loaded && !permissions.error && !permissions.can(resource, 'view');
 const hasCampus = Boolean(config?.columns.includes('branch_name'));
 const campuses = useLookupOptions('lookups/campuses', {}, 'All campuses', hasCampus && !denied);
 const classes = useLookupOptions('classes', { branch_id: params.get('branch_id') || undefined }, 'All classes', classFilter(resource) && !denied);

 const filter = (key: string, value: string) => setParams(current => {
  const next = new URLSearchParams(current); if (value) next.set(key, value); else next.delete(key);
  if (key !== 'page') next.delete('page'); if (key === 'branch_id') next.delete('school_class_id');
  return next;
 });
 useEffect(() => { setSearch(params.get('search') || ''); }, [resource]);
 useEffect(() => { if (debounced !== (params.get('search') || '')) filter('search', debounced); }, [debounced]);
 useEffect(() => {
  let active = true; setStatuses([]);
  if (config && !denied) sisApi.schema(resource).then(r => { const field = r.data.find(f => f.name === 'status'); if (active && field?.choices) setStatuses(field.choices.map(c => ({ value: c.value, label: c.label }))); }).catch(() => undefined);
  return () => { active = false; };
 }, [resource, denied]);
 useEffect(() => {
  let active = true; setError(''); if (!config || denied) { setLoading(false); return; }
  setLoading(true);
  sisApi.list(resource, { page_size: 25, ...Object.fromEntries(params) }).then(r => { if (active) setData(r.data); }).catch(e => { if (active) { setData(undefined); setError(e.message); } }).finally(() => { if (active) setLoading(false); });
  return () => { active = false; };
 }, [resource, query, retry, denied]);

 if (!config) return <PageLayout title="School" breadcrumbs={['School']}><ErrorBanner message="This School area does not exist."/></PageLayout>;

 const archive = async (row: Row, restore: boolean) => {
  const verb = restore ? 'Restore' : 'Archive';
  if (!await appDialog.confirm(`${verb} ${row.name || singular(resource).toLowerCase()}?`, { title: `${verb} ${singular(resource).toLowerCase()}`, confirmLabel: verb, tone: restore ? 'default' : 'danger' })) return;
  try { await sisApi.action(resource, row.id, restore ? 'restore' : 'archive'); setRetry(v => v + 1); } catch (e) { setError(e instanceof Error ? e.message : 'Action failed.'); }
 };
 const rowActions = (row: Row): MenuItem[] => {
  const items: MenuItem[] = [{ label: 'View details', to: `${path(resource)}/${row.id}${archived ? '?archived=true' : ''}` }];
  if (!archived && editable(resource) && permissions.can(resource, 'update')) items.push({ label: 'Edit', to: `${path(resource)}/${row.id}/edit` });
  if (!immutable(resource) && permissions.can(resource, archived ? 'restore' : 'archive')) items.push({ label: archived ? 'Restore' : 'Archive', destructive: !archived, onSelect: () => void archive(row, archived) });
  return items;
 };
 const parents = parentFilters(params);
 const canCreate = !config.readonly && permissions.can(resource, 'create') && (resource !== 'students' || permissions.can(resource, 'create_direct'));
 const createQuery = new URLSearchParams(parents).toString();
 const workflow = WORKFLOW_ENTRY[resource] && WORKFLOW_ENTRY[resource].codes.some(code => permissions.codes.includes(code)) ? WORKFLOW_ENTRY[resource] : undefined;
 const filters: FilterConfig[] = [
  ...(statuses.length ? [{ key: 'status', label: 'Status', value: params.get('status') || '', onChange: (v: string) => filter('status', v), options: [{ value: '', label: 'All statuses' }, ...statuses] }] : []),
  ...(hasCampus && campuses.length > 2 ? [{ key: 'branch_id', label: 'Campus', value: params.get('branch_id') || '', onChange: (v: string) => filter('branch_id', v), options: campuses }] : []),
  ...(classFilter(resource) ? [{ key: 'school_class_id', label: 'Class', value: params.get('school_class_id') || '', onChange: (v: string) => filter('school_class_id', v), options: classes }] : []),
  { key: 'ordering', label: 'Sort', value: params.get('ordering') || '-created_at', onChange: (v: string) => filter('ordering', v || '-created_at'), options: [{ value: '-created_at', label: 'Newest first' }, { value: 'created_at', label: 'Oldest first' }] },
 ];

 return <PageLayout title={config.title} description={description(resource)} breadcrumbs={schoolBreadcrumbs(location.pathname, config.title)}
  actions={canCreate ? <Button asChild size="sm"><Link to={`${path(resource)}/new${createQuery ? `?${createQuery}` : ''}`}><Plus className="mr-2 h-4 w-4"/>New {singular(resource).toLowerCase()}</Link></Button> : workflow ? <Button asChild size="sm"><Link to={workflow.to}><Plus className="mr-2 h-4 w-4"/>{workflow.label}</Link></Button> : undefined}>
  {permissions.error && <ErrorBanner message={permissions.error} onRetry={permissions.load} retryLabel="Retry permissions"/>}
  {denied ? <ContentSection><PermissionDenied message={`Your role cannot view ${config.title.toLowerCase()}.`}/></ContentSection> : <>
   {parents.length > 0 && <div role="status" className="flex flex-wrap items-center gap-3 rounded-xl border bg-muted/40 px-4 py-2.5 text-sm">
    <span>Showing records for the selected {parents.map(([key]) => label(key).toLowerCase()).join(', ')}.</span>
    <Button size="sm" variant="ghost" onClick={() => setParams(new URLSearchParams([...params].filter(([key]) => !parents.some(([p]) => p === key))))}><X className="mr-1 h-3.5 w-3.5"/>Clear filter</Button>
   </div>}
   {error && <ErrorBanner message={error} onRetry={() => setRetry(v => v + 1)}/>}
   <DataTable
    columns={listColumns(resource, archived, rowActions)} data={data?.results || []} loading={loading}
    page={data?.page || Number(params.get('page') || 1)} pageSize={Number(params.get('page_size') || 25)} total={data?.count || 0}
    onPageChange={p => filter('page', String(p))} onPageSizeChange={size => filter('page_size', String(size))}
    searchValue={search} onSearchChange={setSearch} searchPlaceholder={`Search ${config.title.toLowerCase()}…`} filters={filters}
    exportTitle={`${config.title} — page ${data?.page || 1}`}
    onExport={exportable(resource) && permissions.can(resource, 'export') ? () => void download(`${resource}/export/?${query}`, `${resource}.csv`).catch(e => setError(e.message)) : undefined}
    actions={!immutable(resource) ? <label className="flex h-9 items-center gap-2 rounded-lg border px-3 text-sm"><input type="checkbox" checked={archived} onChange={e => filter('archived', e.target.checked ? 'true' : '')}/>Archived</label> : undefined}
    emptyMessage={error ? 'Records could not be loaded.' : params.get('search') || params.get('status') ? `No ${config.title.toLowerCase()} match these filters.` : `No ${config.title.toLowerCase()} yet.`}
   />
  </>}
 </PageLayout>;
}
