import { useEffect, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import { schoolBreadcrumbs } from '@/navigation/schoolNavigation';
import { ErrorBanner } from '../components/SchoolUi';
import { PageLayout } from '@/components/layout/PageLayout';
import { FormSection } from '@/components/forms/FormField';
import { Button } from '@/components/ui/button';
import { schoolApi } from '@/services/api/school';
import { ApiClientError } from '@/services/api/http';
import { resources, schoolPath, formPayload } from '../foundation';
import { useCapabilities } from '../hooks/useFoundation';
import { FoundationFields } from '../components/FoundationFields';
import { useUnsavedChanges } from '../hooks/useUnsavedChanges';
export function FoundationFormPage() {
    const { resource = 'academic-years', id } = useParams();
    const config = resources[resource];
    const navigate = useNavigate();
    const location = useLocation();
    const { can } = useCapabilities();
    const [values, setValues] = useState<Record<string, unknown>>({});
    const [errors, setErrors] = useState<Record<string, string[]>>({});
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(Boolean(id));
    const [saving, setSaving] = useState(false);
    const submitting = useRef(false);
    const [dirty, setDirty] = useState(false);
    useUnsavedChanges(dirty);
    const [retry, setRetry] = useState(0);
    const defaults = () => Object.fromEntries((config?.fields || []).map(f => [f.key, f.default ?? (f.type === 'checkbox' ? false : f.type === 'select' ? f.options?.[0] : '')]));
    useEffect(() => { let active = true; setError(''); setErrors({}); setValues(defaults()); if (!id) {
        setLoading(false);
        return;
    } setLoading(true); schoolApi.detail(resource, id).then(r => { if (active)
        setValues(r.data); }).catch(e => { if (active)
        setError(e.message); }).finally(() => { if (active)
        setLoading(false); }); return () => { active = false; }; }, [resource, id, retry]);
    if (!config)
        return <PageLayout title="School"><p>Academic area not found.</p></PageLayout>;
    const change = (key: string, value: unknown) => { setDirty(true); setValues(v => {
        const next = { ...v, [key]: value };
        if (key === 'branch_id')
            for (const field of ['academic_year_id', 'term_id', 'school_class_id', 'section_id', 'teacher_id', 'shift_id'])
                next[field] = '';
        if (key === 'academic_year_id')
            next.term_id = '';
        if (key === 'school_class_id')
            next.section_id = '';
        return next;
    }); };
    const submit = async (another = false) => { if (submitting.current) return; submitting.current = true; setSaving(true); setError(''); setSuccess(''); setErrors({}); try {
        const r = await schoolApi.save(resource, formPayload(config.fields, values), id);
        setDirty(false);
        if (another) {
            setValues(defaults());
            setSuccess(`${config.singular} saved. You can create another.`);
            setError('');
        }
        else
            navigate(`${schoolPath(resource)}/${r.data.id}`);
    }
    catch (e) {
        if (e instanceof ApiClientError)
            setErrors(e.fieldErrors);
        setError(e instanceof Error ? e.message : 'Could not save.');
    }
    finally {
        submitting.current = false; setSaving(false);
    } };
    const permitted = can(resource, id ? 'update' : 'create');
    return <PageLayout title={`${id ? 'Edit' : 'Create'} ${config.singular.toLowerCase()}`} description={config.description} breadcrumbs={schoolBreadcrumbs(location.pathname, config.title, id ? 'Edit' : 'Create')} backTo={id ? `${schoolPath(resource)}/${id}` : schoolPath(resource)} backLabel="Back">
  {error && <ErrorBanner message={error} onRetry={id ? () => setRetry(v => v + 1) : undefined} retryLabel="Reload record"/>}
  {success && <p role="status" className="mb-4 text-sm text-emerald-700">{success}</p>}
  {!permitted && <p role="status" className="mb-4 text-sm text-muted-foreground">You need permission to save changes in this area.</p>}
  <form onSubmit={e => { e.preventDefault(); void submit(); }}>
   <div className="space-y-5">{[
       { title: 'Basic information', keys: ['name', 'code', 'description', 'short_name'] },
       { title: 'Campus & staff references', keys: ['branch_id', 'company_id', 'room', 'teacher_id', 'user_id', 'shift_id'] },
       { title: 'Academic configuration', keys: config.fields.map(f => f.key).filter(key => !['name', 'code', 'description', 'short_name', 'branch_id', 'company_id', 'room', 'teacher_id', 'user_id', 'shift_id'].includes(key)) },
   ].filter(group => config.fields.some(f => group.keys.includes(f.key))).map(group => <FormSection key={group.title} title={group.title}>
       <FoundationFields fields={config.fields.filter(f => group.keys.includes(f.key))} values={values} onChange={change} errors={errors} editing={Boolean(id)} disabled={loading || saving || !permitted}/>
   </FormSection>)}</div>
   <div className="sticky bottom-0 mt-6 flex flex-wrap justify-end gap-3 rounded-xl border bg-card p-4">
    <Button asChild variant="outline" type="button"><Link to={schoolPath(resource)}>Cancel</Link></Button>
    {!id && permitted && <Button type="button" variant="secondary" disabled={saving || loading} onClick={e => { if (e.currentTarget.form?.reportValidity())
        void submit(true); }}>Save & new</Button>}
    {permitted && <Button type="submit" loading={saving} disabled={loading || (Boolean(id) && Boolean(error) && Object.keys(errors).length === 0)}>Save {config.singular.toLowerCase()}</Button>}
   </div>
  </form>
 </PageLayout>;
}
