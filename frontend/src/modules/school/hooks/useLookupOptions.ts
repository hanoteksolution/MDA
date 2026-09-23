import { useEffect, useState } from 'react';
import { schoolApi } from '@/services/api/school';
import type { FilterOption } from '@/components/data/FilterBar';

/** Options for a toolbar filter, loaded from an existing School list/lookup endpoint. */
export function useLookupOptions(resource: string, params: Record<string, string | undefined>, allLabel: string, enabled = true): FilterOption[] {
    const [options, setOptions] = useState<FilterOption[]>([]);
    const key = JSON.stringify(params);
    useEffect(() => {
        let active = true;
        if (!enabled) { setOptions([]); return; }
        schoolApi.list(resource, { ...params, page_size: 100 })
            .then(r => { if (active) setOptions(r.data.results.map(row => ({ value: row.id, label: String(row.name || row.school_name || row.code || row.id) }))); })
            .catch(() => { if (active) setOptions([]); });
        return () => { active = false; };
    }, [resource, key, enabled]);
    return [{ value: '', label: allLabel }, ...options];
}

export type LookupSpec = { resource: string; params: Record<string, string | undefined>; allLabel: string };

/** Batched variant for a variable number of toolbar filters (hook count stays constant). */
export function useLookupGroups(specs: LookupSpec[]): FilterOption[][] {
    const [groups, setGroups] = useState<FilterOption[][]>([]);
    const key = JSON.stringify(specs);
    useEffect(() => {
        let active = true;
        Promise.all(specs.map(spec => schoolApi.list(spec.resource, { ...spec.params, page_size: 100 })
            .then(r => r.data.results.map(row => ({ value: row.id, label: String(row.name || row.school_name || row.code || row.id) })))
            .catch(() => [] as FilterOption[])))
            .then(results => { if (active) setGroups(results); });
        return () => { active = false; };
    }, [key]);
    return specs.map((spec, i) => [{ value: '', label: spec.allLabel }, ...(groups[i] || [])]);
}
