import { Input } from '@/components/ui/input';
import { FormField, FormGrid } from '@/components/forms/FormField';
import { RelationField } from './RelationField';
import type { Field, SchoolRecord } from '../foundation';
export function FoundationFields({ fields, values, onChange, errors = {}, editing = false, disabled = false }: {
    fields: Field[];
    values: SchoolRecord | Record<string, unknown>;
    onChange: (key: string, value: unknown) => void;
    errors?: Record<string, string[]>;
    editing?: boolean;
    disabled?: boolean;
}) {
    return <FormGrid>{fields.map(f => {
            const locked = disabled || Boolean(editing && f.immutable);
            const value = values[f.key];
            const params: Record<string, string | undefined> = {};
            if (f.key !== 'branch_id' && values.branch_id)
                params.branch_id = String(values.branch_id);
            if (f.key === 'term_id' && values.academic_year_id)
                params.academic_year_id = String(values.academic_year_id);
            if (f.key === 'section_id' && values.school_class_id)
                params.school_class_id = String(values.school_class_id);
            return <FormField key={f.key} label={f.label} htmlFor={f.key} required={f.required}>
   {f.type === 'relation' ? <RelationField id={f.key} label={f.label} resource={f.resource!} value={String(value || '')} currentLabel={String(values[f.key.replace('_id', '_name')] || '')} onChange={v => onChange(f.key, v)} params={params} required={f.required} disabled={locked}/> :
                    f.type === 'checkbox' ? <input id={f.key} aria-label={f.label} type="checkbox" className="h-5 w-5 accent-emerald-600" checked={Boolean(value)} disabled={locked} onChange={e => onChange(f.key, e.target.checked)}/> :
                        f.type === 'select' ? <select id={f.key} aria-label={f.label} className="h-10 w-full rounded-lg border border-input bg-background px-3" value={String(value || f.default || f.options?.[0] || '')} disabled={locked} onChange={e => onChange(f.key, e.target.value)}>{f.options?.map(v => <option key={v} value={v}>{v.replace(/_/g, ' ')}</option>)}</select> :
                            <Input id={f.key} aria-label={f.label} aria-invalid={Boolean(errors[f.key])} aria-describedby={errors[f.key] ? `${f.key}-error` : undefined} type={f.type || 'text'} step={f.type === 'number' ? 'any' : undefined} value={String(value ?? '')} required={f.required} disabled={locked} onChange={e => onChange(f.key, e.target.value)}/>}
   {errors[f.key] && <p id={`${f.key}-error`} role="alert" className="text-sm text-destructive">{errors[f.key].join(' ')}</p>}
  </FormField>;
        })}</FormGrid>;
}
