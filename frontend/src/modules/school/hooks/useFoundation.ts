import { useEffect, useState } from 'react';
import { schoolApi } from '@/services/api/school';
import { useAuthStore } from '@/store/authStore';
export function useCapabilities() {
    const user = useAuthStore(s => s.user);
    const [data, setData] = useState<Record<string, string[]>>({});
    const [error, setError] = useState('');
    const [attempt, setAttempt] = useState(0);
    const [loaded, setLoaded] = useState(false);
    useEffect(() => { let current = true; setData({}); setError(''); setLoaded(false); schoolApi.capabilities().then(r => { if (current)
        setData(r.data); }).catch(e => { if (current)
        setError(e.message); }).finally(() => { if (current)
        setLoaded(true); }); return () => { current = false; }; }, [user, attempt]);
    return { can: (resource: string, action: string) => data[resource]?.includes(action) ?? false, loaded, error, retry: () => setAttempt(value => value + 1) };
}
export function useDebounced(value: string) {
    const [result, setResult] = useState(value);
    useEffect(() => { const t = setTimeout(() => setResult(value), 250); return () => clearTimeout(t); }, [value]);
    return result;
}
