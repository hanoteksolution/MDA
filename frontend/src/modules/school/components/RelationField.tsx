import { useEffect, useState } from 'react';
import { schoolApi } from '@/services/api/school';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useDebounced } from '../hooks/useFoundation';
import type { SchoolRecord } from '../foundation';
export function RelationField({ id, label, resource, value, onChange, params = {}, required = false, disabled = false, currentLabel }: {
    id: string;
    label: string;
    resource: string;
    value: string;
    onChange: (v: string) => void;
    params?: Record<string, string | undefined>;
    required?: boolean;
    disabled?: boolean;
    currentLabel?: string;
}) {
    const [search, setSearch] = useState('');
    const debounced = useDebounced(search);
    const [page, setPage] = useState(1);
    const [rows, setRows] = useState<SchoolRecord[]>([]);
    const [pages, setPages] = useState(1);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const key = JSON.stringify(params);
    useEffect(() => setPage(1), [debounced, key]);
    useEffect(() => {
        let active = true;
        if (disabled)
            return;
        if (resource.startsWith('lookups/') && !['lookups/campuses', 'lookups/companies'].includes(resource) && !params.branch_id) {
            setRows([]);
            return;
        }
        setLoading(true);
        setError('');
        schoolApi.list(resource, { ...params, search: debounced, page, page_size: 20 }).then(r => { if (active) {
            setRows(r.data.results.filter(x => x.eligible !== false));
            setPages(r.data.total_pages);
        } }).catch(e => { if (active)
            setError(e.message); }).finally(() => { if (active)
            setLoading(false); });
        return () => { active = false; };
    }, [resource, debounced, page, key, disabled]);
    return <div className="space-y-2">
  {!disabled && <Input aria-label={`Search ${label}`} placeholder={`Search ${label.toLowerCase()}…`} value={search} onChange={e => setSearch(e.target.value)}/>}
  <select id={id} aria-label={label} required={required} disabled={disabled || loading} className="h-10 w-full rounded-lg border border-input bg-background px-3 text-sm" value={value} onChange={e => onChange(e.target.value)}>
   <option value="">{loading ? 'Loading…' : `Select ${label.toLowerCase()}`}</option>
   {value && !rows.some(r => r.id === value) && <option value={value}>{currentLabel || value}</option>}
   {rows.map(r => <option key={r.id} value={r.id}>{String(r.name || r.school_name || r.code || r.id)}</option>)}
  </select>
  {error && <p role="alert" className="text-sm text-destructive">{error}</p>}
  {!disabled && pages > 1 && <div className="flex items-center gap-2"><Button type="button" size="sm" variant="ghost" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button><span className="text-xs text-muted-foreground">{page} / {pages}</span><Button type="button" size="sm" variant="ghost" disabled={page >= pages} onClick={() => setPage(page + 1)}>Next</Button></div>}
 </div>;
}
