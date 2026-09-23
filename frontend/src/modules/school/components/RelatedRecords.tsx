import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { schoolApi } from '@/services/api/school';
import { Button } from '@/components/ui/button';
import { schoolPath, type SchoolRecord } from '../foundation';
export function RelatedRecords({ resource, params }: {
    resource: string;
    params: Record<string, string>;
}) {
    const [rows, setRows] = useState<SchoolRecord[]>([]);
    const [page, setPage] = useState(1);
    const [pages, setPages] = useState(1);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(true);
    const key = JSON.stringify(params);
    useEffect(() => { let current = true; setLoading(true); setError(''); schoolApi.list(resource, { ...params, page }).then(r => { if (current) {
        setRows(r.data.results);
        setPages(r.data.total_pages);
    } }).catch(e => { if (current)
        setError(e.message); }).finally(() => { if (current)
        setLoading(false); }); return () => { current = false; }; }, [resource, key, page]);
    if (loading)
        return <p role="status" className="p-4 text-muted-foreground">Loading related records…</p>;
    if (error)
        return <p role="alert" className="p-4 text-destructive">{error}</p>;
    return <div className="divide-y rounded-xl border">{rows.length ? rows.map(r => <div key={r.id} className="p-4">{r.action ? <><p className="font-medium">{String(r.action).replace(/_/g, ' ')}</p><p className="text-xs text-muted-foreground">{String(r.timestamp)}</p></> : <Link className="font-medium text-primary" to={`${schoolPath(resource)}/${r.id}`}>{String(r.name || r.code)}</Link>}</div>) : <p className="p-4 text-muted-foreground">No related records.</p>}{pages > 1 && <div className="flex justify-between p-3"><Button variant="ghost" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</Button><span>{page} / {pages}</span><Button variant="ghost" disabled={page === pages} onClick={() => setPage(page + 1)}>Next</Button></div>}</div>;
}
