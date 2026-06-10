import type { ApiResponse } from "@/types/models";
import type { AdminUser, BranchDetail, Company, RoleDetail, SystemSetting } from "@/types/models/admin";
import { apiRequest } from "./http";

export const settingsApi = {
  company: () => apiRequest<ApiResponse<Company | null>>("/settings/company/"),

  updateCompany: (data: Partial<Company>) =>
    apiRequest<ApiResponse<Company>>("/settings/company/", {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  branches: () => apiRequest<ApiResponse<BranchDetail[]>>("/settings/branches/"),

  createBranch: (data: Partial<BranchDetail> & { company_id?: string }) =>
    apiRequest<ApiResponse<BranchDetail>>("/settings/branches/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateBranch: (id: string, data: Partial<BranchDetail>) =>
    apiRequest<ApiResponse<BranchDetail>>(`/settings/branches/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  setDefaultBranch: (id: string) =>
    apiRequest<ApiResponse<BranchDetail>>(`/settings/branches/${id}/set-default/`, {
      method: "POST",
    }),

  list: (category?: string) =>
    apiRequest<ApiResponse<SystemSetting[]>>(
      `/settings/${category ? `?category=${category}` : ""}`
    ),
};

export const adminApi = {
  users: (search?: string) =>
    apiRequest<ApiResponse<AdminUser[]>>(
      `/users/${search ? `?search=${encodeURIComponent(search)}` : ""}`
    ),

  getUser: (id: string) => apiRequest<ApiResponse<AdminUser>>(`/users/${id}/`),

  createUser: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<AdminUser>>("/users/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateUser: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<AdminUser>>(`/users/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deactivateUser: (id: string) =>
    apiRequest<ApiResponse<null>>(`/users/${id}/`, { method: "DELETE" }),

  roles: () => apiRequest<ApiResponse<RoleDetail[]>>("/roles/"),

  getRole: (id: string) => apiRequest<ApiResponse<RoleDetail>>(`/roles/${id}/`),

  createRole: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<RoleDetail>>("/roles/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateRole: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<RoleDetail>>(`/roles/${id}/`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteRole: (id: string) =>
    apiRequest<ApiResponse<null>>(`/roles/${id}/`, { method: "DELETE" }),

  permissions: () =>
    apiRequest<ApiResponse<Record<string, { id: string; name: string; codename: string; module: string }[]>>>(
      "/roles/permissions/"
    ),
};
