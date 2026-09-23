import * as Dropdown from '@radix-ui/react-dropdown-menu';
import { MoreHorizontal, ShieldAlert, AlertTriangle } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge, type BadgeProps } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/layout/EmptyState';
import { LoadingState } from '@/components/layout/LoadingState';
import { cn } from '@/utils/cn';

const TONES: Record<NonNullable<BadgeProps['variant']>, string[]> = {
    success: ['active', 'current', 'enrolled', 'accepted', 'published', 'verified', 'approved', 'posted', 'issued', 'committed', 'passed', 'completed', 'present', 'paid', 'promoted', 'graduated'],
    warning: ['draft', 'pending', 'requested', 'preview', 'planning', 'waitlisted', 'under_review', 'document_review', 'scheduled', 'open', 'submitted', 'moderated', 'late', 'partially_paid', 'half_day', 'requires_reupload', 'assessment_completed', 'interview_completed'],
    destructive: ['rejected', 'withdrawn', 'cancelled', 'suspended', 'failed', 'fail', 'expired', 'absent', 'reversed', 'overdue', 'void'],
    secondary: ['inactive', 'closed', 'archived', 'transferred', 'excused', 'repeat'],
    default: [],
    outline: [],
};

export function statusTone(status: string): NonNullable<BadgeProps['variant']> {
    const key = status.toLowerCase().replace(/\s+/g, '_');
    for (const [tone, values] of Object.entries(TONES)) if (values.includes(key)) return tone as NonNullable<BadgeProps['variant']>;
    return 'outline';
}

/** One status vocabulary for every School list, detail and dashboard. */
export function SchoolStatusBadge({ status, className }: { status: unknown; className?: string }) {
    if (status === null || status === undefined || status === '') return <span className="text-muted-foreground">—</span>;
    const value = String(status);
    return <Badge variant={statusTone(value)} className={cn('whitespace-nowrap capitalize', className)}>{value.replace(/_/g, ' ')}</Badge>;
}

export function ErrorBanner({ message, onRetry, retryLabel = 'Retry' }: { message: string; onRetry?: () => void; retryLabel?: string }) {
    return <div role="alert" className="flex flex-wrap items-center gap-3 rounded-xl border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
        <AlertTriangle className="h-4 w-4 shrink-0" aria-hidden/>
        <span className="flex-1">{message}</span>
        {onRetry && <Button size="sm" variant="outline" onClick={onRetry}>{retryLabel}</Button>}
    </div>;
}

export function PermissionDenied({ message = 'Your role does not include access to this area.' }: { message?: string }) {
    return <EmptyState compact icon={<ShieldAlert className="h-5 w-5"/>} title="Permission required" description={message}/>;
}

/** Permission gate for workflow pages: skeleton until capabilities load, then the denied state. */
export function Denied({ loaded, message }: { loaded: boolean; message: string }) {
    return loaded ? <PermissionDenied message={message}/> : <LoadingState variant="rows" rows={3} label="Checking permissions"/>;
}

export type MenuItem = { label: string; to?: string; onSelect?: () => void; destructive?: boolean };

/** Row action dropdown (⋮) used by every School table. */
export function RecordMenu({ label, items }: { label: string; items: MenuItem[] }) {
    if (!items.length) return null;
    const item = 'block w-full cursor-pointer rounded-md px-3 py-2 text-left text-sm outline-none focus:bg-muted';
    return <Dropdown.Root><Dropdown.Trigger asChild><Button variant="ghost" size="sm" aria-label={`Actions for ${label}`}><MoreHorizontal className="h-4 w-4"/></Button></Dropdown.Trigger><Dropdown.Portal><Dropdown.Content align="end" className="z-50 min-w-44 rounded-xl border bg-popover p-1 shadow-lg">
        {items.map(entry => entry.to
            ? <Dropdown.Item key={entry.label} asChild><Link className={item} to={entry.to}>{entry.label}</Link></Dropdown.Item>
            : <Dropdown.Item key={entry.label} className={cn(item, entry.destructive && 'text-destructive')} onSelect={entry.onSelect}>{entry.label}</Dropdown.Item>)}
    </Dropdown.Content></Dropdown.Portal></Dropdown.Root>;
}

/** Definition list used on School detail pages. */
export function DetailGrid({ items }: { items: { label: string; value: React.ReactNode }[] }) {
    return <dl className="grid gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-3">{items.map(entry => <div key={entry.label} className="min-w-0"><dt className="text-xs font-medium text-muted-foreground">{entry.label}</dt><dd className="mt-1 whitespace-pre-wrap break-words text-sm">{entry.value}</dd></div>)}</dl>;
}
