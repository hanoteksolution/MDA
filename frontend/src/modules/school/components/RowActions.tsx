import type { SchoolRecord } from '../foundation';
import { resources, schoolPath, lifecycleActions } from '../foundation';
import { RecordMenu, type MenuItem } from './SchoolUi';
export function RowActions({ resource, row, can, onAction }: {
    resource: string;
    row: SchoolRecord;
    can: (action: string) => boolean;
    onAction: (action: string) => void;
}) {
    const archived = Boolean(row.deleted_at) || (resource === 'campuses' && row.is_active === false);
    const items: MenuItem[] = [{ label: 'View details', to: `${schoolPath(resource)}/${row.id}${archived ? '?archived=true' : ''}` }];
    if (!archived && row.status !== 'closed' && can('update')) items.push({ label: 'Edit', to: `${schoolPath(resource)}/${row.id}/edit` });
    for (const a of lifecycleActions(resources[resource], row, can))
        items.push({ label: a === 'activate' && resource === 'academic-years' ? 'Make current' : a[0].toUpperCase() + a.slice(1), destructive: a === 'archive' || a === 'close', onSelect: () => onAction(a) });
    return <RecordMenu label={String(row.name || row.id)} items={items}/>;
}
