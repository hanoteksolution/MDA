import { describe, it, expect, vi } from 'vitest';
vi.mock('@/store/authStore', () => ({ useAuthStore: () => null }));
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { FoundationFields } from './components/FoundationFields';
import { formPayload, lifecycleActions, resources } from './foundation';
describe('School foundation form contracts', () => {
    it('sends only editable fields and keeps null optional relationships', () => {
        const payload = formPayload(resources.classes.fields, { id: 'record', tenant_id: 'injected', name: 'Grade 5', code: 'G5', capacity: '30', teacher_id: '', status: 'active' });
        expect(payload).not.toHaveProperty('tenant_id');
        expect(payload).not.toHaveProperty('id');
        expect(payload.teacher_id).toBeNull();
        expect(payload.capacity).toBe('30');
    });
    it('cannot expose activate or archive to a reader', () => {
        expect(lifecycleActions(resources['academic-years'], { id: 'y', status: 'planning' }, () => false)).toEqual([]);
    });
    it('only offers restore for archived records and never reactivates closed years', () => {
        expect(lifecycleActions(resources['academic-years'], { id: 'y', status: 'archived', deleted_at: '2026-09-01' }, () => true)).toEqual(['restore']);
        expect(lifecycleActions(resources['academic-years'], { id: 'y', status: 'closed' }, () => true)).toEqual(['archive']);
    });
    it('renders linked labels, inline errors and responsive field grid', () => {
        const html = renderToStaticMarkup(createElement(FoundationFields, { fields: [{ key: 'name', label: 'Class name', required: true }], values: { name: '' }, errors: { name: ['Name is required.'] }, onChange: () => { } }));
        expect(html).toContain('for="name"');
        expect(html).toContain('aria-invalid="true"');
        expect(html).toContain('role="alert"');
        expect(html).toContain('Name is required.');
        expect(html).toContain('md:grid-cols-2');
    });
    it('disables identity fields on edit', () => {
        const html = renderToStaticMarkup(createElement(FoundationFields, { fields: [{ key: 'branch_id', label: 'Campus', type: 'relation', resource: 'lookups/campuses', immutable: true }], values: { branch_id: 'a', branch_name: 'Campus A' }, editing: true, onChange: () => { } }));
        expect(html).toContain('disabled=""');
        expect(html).toContain('Campus A');
    });
    it('declares complete configuration for every delivered resource', () => {
        for (const r of Object.values(resources)) {
            expect(r.fields.length).toBeGreaterThan(0);
            expect(new Set(r.fields.map(f => f.key)).size).toBe(r.fields.length);
        }
    });
});
