import { useEffect, useRef, useState } from 'react';
import { PageLayout } from '@/components/layout/PageLayout';
import { EmptyState } from '@/components/layout/EmptyState';
import { FormSection } from '@/components/forms/FormField';
import { Button } from '@/components/ui/button';
import { schoolApi } from '@/services/api/school';
import { ApiClientError } from '@/services/api/http';
import { profileFields, formPayload } from '../foundation';
import { FoundationFields } from '../components/FoundationFields';
import { RelationField } from '../components/RelationField';
import { useCapabilities } from '../hooks/useFoundation';
import { useUnsavedChanges } from '../hooks/useUnsavedChanges';
import { ErrorBanner } from '../components/SchoolUi';
export function SchoolSettingsPage() {
    const [branch, setBranch] = useState('');
    const [values, setValues] = useState<Record<string, unknown>>({});
    const [errors, setErrors] = useState<Record<string, string[]>>({});
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const submitting = useRef(false);
    const [dirty, setDirty] = useState(false);
    useUnsavedChanges(dirty);
    const change = (key: string, value: unknown) => { setDirty(true); setValues(current => ({...current, [key]: value})); };
    const [loaded, setLoaded] = useState(false);
    const [success, setSuccess] = useState('');
    const [retry, setRetry] = useState(0);
    const { can } = useCapabilities();
    useEffect(() => { let active = true; setLoaded(false); setError(''); setSuccess(''); if (!branch) {
        setValues({});
        return;
    } setLoading(true); schoolApi.profile(branch).then(r => { if (active) {
        setValues(r.data || r.defaults || {});
        setLoaded(true);
    } }).catch(e => { if (active)
        setError(e.message); }).finally(() => { if (active)
        setLoading(false); }); return () => { active = false; }; }, [branch, retry]);
    const save = async () => { if (submitting.current) return; submitting.current = true; setSaving(true); setError(''); setErrors({}); try {
        const r = await schoolApi.saveProfile({ ...formPayload(profileFields.filter(f => f.key !== 'branch_id'), values), branch_id: branch });
        setValues(r.data);
        setDirty(false);
        setSuccess('School profile saved.');
    }
    catch (e) {
        if (e instanceof ApiClientError)
            setErrors(e.fieldErrors);
        setError(e instanceof Error ? e.message : 'Could not save profile.');
    }
    finally {
        submitting.current = false; setSaving(false);
    } };
    const uploadLogo = async (file: File) => {
        if (submitting.current) return; submitting.current = true; setSaving(true); setError('');
        try {
            const result = await schoolApi.uploadLogo(file, branch);
            setValues(current => ({...current, logo_url: result.data.logo_url}));
            setSuccess('Campus logo updated.');
        } catch (e) { setError(e instanceof Error ? e.message : 'Logo upload failed.'); }
        finally { submitting.current = false; setSaving(false); }
    };
    const fields = profileFields.filter(f => f.key !== 'branch_id');
    return <PageLayout title="School profile" description="Manage campus identity, leadership and academic preferences. Company identity remains in shared ERP settings." breadcrumbs={['School', 'School settings', 'School profile']}>
  <div className="mb-5 max-w-sm"><p className="mb-2 text-sm font-medium">Select campus</p><RelationField id="profile-campus" label="Campus" resource="lookups/campuses" value={branch} disabled={saving} onChange={next => { if (!dirty || window.confirm('Discard your unsaved changes?')) { setDirty(false); setBranch(next); } }}/></div>
  {error && <ErrorBanner message={error} onRetry={() => setRetry(v => v + 1)} retryLabel="Reload profile"/>}
  {success && <p role="status" className="mb-4 text-emerald-600">{success}</p>}
  {!branch ? <EmptyState compact title="Select a campus" description="Choose an accessible campus to view its school profile."/> : <form onSubmit={e => { e.preventDefault(); void save(); }}>
   <div className="mb-5 flex flex-wrap items-center gap-4 rounded-xl border bg-card p-4">
       {Boolean(values.logo_url) && <img src={String(values.logo_url)} alt="Campus logo" className="h-16 w-16 rounded-lg object-contain"/>}
       <label className="text-sm font-medium">Campus logo (JPEG, PNG, WebP or GIF, up to 5 MB)
           <input aria-label="Upload campus logo" type="file" accept="image/jpeg,image/png,image/webp,image/gif" className="mt-2 block max-w-full text-sm" disabled={!loaded || loading || saving || !can('profile','update')} onChange={e => { const file = e.target.files?.[0]; if(file) void uploadLogo(file); e.target.value = ''; }}/>
       </label>
   </div>
   <FormSection title="Identity & leadership"><FoundationFields fields={fields.slice(0, 8)} values={{ ...values, branch_id: branch }} onChange={change} errors={errors} disabled={!loaded || loading || saving || !can('profile', 'update')}/></FormSection>
   <div className="mt-5"><FormSection title="Contact & academic preferences"><FoundationFields fields={fields.slice(8)} values={values} onChange={change} errors={errors} disabled={!loaded || loading || saving || !can('profile', 'update')}/></FormSection></div>
   {can('profile', 'update') && <Button className="mt-5" type="submit" loading={saving} disabled={!loaded || loading}>Save profile</Button>}
  </form>}
 </PageLayout>;
}
