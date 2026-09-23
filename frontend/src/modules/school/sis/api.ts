import { branchHeaders } from '@/services/api/branchContext';
import { apiRequest, qs, refreshAccessToken, isJwtExpired } from '@/services/api/http';
import { getApiBase } from '@/config/api';
export type Row = { id: string; name: string; [key: string]: unknown };
export type Values = Record<string, unknown>;
export type Params = Record<string, string | number | boolean | undefined>;
export interface Page { results: Row[]; count: number; page: number; page_size: number; total_pages: number }
export interface Field { name: string; label: string; kind: string; lookup?: string; sis?: boolean; required?: boolean; nullable?: boolean; choices?: {value: string; label: string}[]; default?: unknown; max_length?: number }
export interface RosterStudent { student_id: string; student_name: string; roll_number: string; status: string | null; remarks: string }
export interface Roster { session: Row | null; students: RosterStudent[] }
interface Envelope<T> { data: T }
const base = '/school/sis/';
export const sisApi = {
 list: (resource: string, params: Params = {}) => apiRequest<Envelope<Page>>(`${base}${resource}/${qs(params)}`),
 detail: (resource: string, id: string, archived = false) => apiRequest<Envelope<Row>>(`${base}${resource}/${id}/${qs({archived})}`),
 save: (resource: string, values: Values, id?: string) => apiRequest<Envelope<Row>>(`${base}${resource}/${id ? id+'/' : ''}`, {method: id ? 'PATCH':'POST', body: JSON.stringify(values)}),
 action: (resource: string, id: string, action: string, values: Values = {}) => apiRequest<Envelope<Row>>(`${base}${resource}/${id}/${action}/`, {method:'POST', body:JSON.stringify(values)}),
 schema: (resource: string) => apiRequest<Envelope<Field[]>>(`${base}${resource}/schema/`),
 marksRoster: (id: string) => apiRequest<Envelope<MarksRoster>>(`${base}marks-roster/${id}/`),
 financeSummary: (params: Params) => apiRequest<Envelope<Values>>(`${base}finance-summary/${qs(params)}`),
 capabilities: () => apiRequest<Envelope<string[]>>(`${base}capabilities/`),
 dashboard: (params: Params) => apiRequest<Envelope<Values>>(`${base}dashboard/${qs(params)}`),
 roster: (params: Params) => apiRequest<Envelope<Roster>>(`${base}attendance-roster/${qs(params)}`),
 take: (values: Values) => apiRequest<Envelope<Row>>(`${base}attendance-sessions/`, {method:'POST', body:JSON.stringify(values)}),
 duplicates: (values: Values) => apiRequest<Envelope<Row[]>>(`${base}duplicates/`, {method:'POST',body:JSON.stringify(values)}),
};
async function binary(endpoint: string, options: RequestInit = {}, retry = true): Promise<Response> {
 let token = localStorage.getItem('access_token');
 if (token && isJwtExpired(token)) token = await refreshAccessToken();
 const response = await fetch(`${getApiBase()}${base}${endpoint}`, {...options, headers: {...branchHeaders(), ...options.headers, Authorization:`Bearer ${token || ''}`}});
 if (response.status === 401 && retry && await refreshAccessToken()) return binary(endpoint, options, false);
 if (!response.ok) { const error = await response.json().catch(() => ({})); throw new Error(error.message || `Request failed (${response.status}).`); }
 return response;
}
export async function upload(file: File, branch: string, purpose: string): Promise<Row> {
 const body = new FormData(); body.append('file',file);
 return (await (await binary(`files/${qs({branch_id:branch,purpose})}`,{method:'POST',body})).json()).data as Row;
}
export async function download(endpoint: string, filename: string, preview = false) {
 const blob = await (await binary(endpoint)).blob(); const url = URL.createObjectURL(blob);
 if (preview) { const opened = window.open(url,'_blank','noopener,noreferrer'); void opened; }
 else { const link = document.createElement('a'); link.href=url;link.download=filename;link.click(); }
 window.setTimeout(() => URL.revokeObjectURL(url),60000);
}

export interface MarkRow {enrollment_id:string;student_id:string;name:string;score:string|null;outcome:string;remarks:string}
export interface MarksRoster {exam_id:string;revision:number;status:string;maximum_score:string;students:MarkRow[]}
