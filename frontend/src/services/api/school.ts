import { apiRequest, apiUpload, qs } from './http';
import type { SchoolRecord } from '@/modules/school/foundation';
export interface SchoolPageData {
    results: SchoolRecord[];
    count: number;
    page: number;
    page_size: number;
    total_pages: number;
}
interface Envelope<T> {
    success: boolean;
    data: T;
    message?: string;
    defaults?: Record<string, unknown>;
}
export const schoolApi = {
    uploadLogo: (file: File, branchId: string) => apiUpload<Envelope<SchoolRecord>>(`/school/profile/logo/${qs({branch_id: branchId})}`, file),
    list: (resource: string, params: Record<string, string | number | boolean | undefined> = {}) => apiRequest<Envelope<SchoolPageData>>(`/school/${resource}/${qs(params)}`),
    detail: (resource: string, id: string, archived = false) => apiRequest<Envelope<SchoolRecord>>(`/school/${resource}/${id}/${qs({ archived })}`),
    save: (resource: string, data: Record<string, unknown>, id?: string) => apiRequest<Envelope<SchoolRecord>>(`/school/${resource}/${id ? `${id}/` : ''}`, { method: id ? 'PATCH' : 'POST', body: JSON.stringify(data) }),
    action: (resource: string, id: string, action: string) => apiRequest<Envelope<SchoolRecord>>(`/school/${resource}/${id}/${action}/`, { method: 'POST', body: '{}' }),
    profile: (branchId: string) => apiRequest<Envelope<SchoolRecord | null>>(`/school/profile/${qs({ branch_id: branchId })}`),
    saveProfile: (data: Record<string, unknown>) => apiRequest<Envelope<SchoolRecord>>('/school/profile/', { method: 'PUT', body: JSON.stringify(data) }),
    summary: (branchId?: string) => apiRequest<Envelope<Record<string, unknown>>>(`/school/summary/${qs({ branch_id: branchId })}`),
    capabilities: () => apiRequest<Envelope<Record<string, string[]>>>('/school/capabilities/'),
};
