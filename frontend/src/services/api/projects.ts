import type { ApiListResponse } from "@/types/models/catalog";
import type { ApiResponse } from "@/types/models";
import { apiRequest, qs } from "./http";

export interface ProjectSummary {
  total_projects: number;
  active_projects: number;
  completed_projects: number;
  delayed_projects: number;
  at_risk_projects: number;
  total_budget: number;
  total_contract_value: number;
  total_expected_revenue: number;
  total_cost_estimate: number;
  tasks_count: number;
  workers_count: number;
  open_risks_count: number;
  open_issues_count: number;
}

export interface Project {
  id: string;
  branch_id: string;
  branch_name: string;
  client_id: string | null;
  client_name: string;
  project_manager_id: string | null;
  project_manager_name: string;
  cost_center_id: string | null;
  cost_center_code: string;
  project_code: string;
  name: string;
  project_type: string;
  owner_name: string;
  location: string;
  description: string;
  start_date: string | null;
  planned_end_date: string | null;
  actual_end_date: string | null;
  status: string;
  priority: string;
  health: string;
  progress_percent: number;
  budget: number;
  contract_value: number;
  expected_revenue: number;
  cost_estimate: number;
  profit_estimate: number;
  currency: string;
  tax_rate: number;
  payment_terms: string;
  notes: string;
  is_archived: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface WbsNode {
  id: string;
  project_id: string;
  project_code: string;
  project_name: string;
  parent_id: string | null;
  parent_code: string;
  parent_name: string;
  code: string;
  name: string;
  node_type: string;
  description: string;
  sort_order: number;
  level: number;
  planned_start: string | null;
  planned_end: string | null;
  actual_start: string | null;
  actual_end: string | null;
  status: string;
  progress_percent: number;
  estimated_hours: number;
  estimated_cost: number;
  notes: string;
  children?: WbsNode[];
  created_at: string | null;
  updated_at: string | null;
}

export const projectsApi = {
  summary: (branchId?: string) =>
    apiRequest<ApiResponse<ProjectSummary>>(`/projects/summary/${qs({ branch_id: branchId })}`),

  list: (page = 1, branchId?: string, filters?: { status?: string; project_type?: string; search?: string }) =>
    apiRequest<ApiListResponse<Project>>(
      `/projects/${qs({ page, branch_id: branchId, ...filters })}`
    ),

  get: (id: string) => apiRequest<ApiResponse<Project>>(`/projects/${id}/`),

  create: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Project>>("/projects/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  update: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Project>>(`/projects/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  archive: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/projects/${id}/`, {
      method: "DELETE",
    }),

  restore: (id: string) =>
    apiRequest<ApiResponse<Project>>(`/projects/${id}/restore/`, {
      method: "POST",
    }),

  setStatus: (id: string, status: string) =>
    apiRequest<ApiResponse<Project>>(`/projects/${id}/status/`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),

  duplicate: (id: string) =>
    apiRequest<ApiResponse<Project>>(`/projects/${id}/duplicate/`, {
      method: "POST",
    }),

  budgets: (page = 1, projectId?: string, branchId?: string) =>
    apiRequest<ApiListResponse<ProjectBudget>>(
      `/projects/budgets/${qs({ page, project_id: projectId, branch_id: branchId })}`
    ),

  budget: (id: string) => apiRequest<ApiResponse<ProjectBudget>>(`/projects/budgets/${id}/`),

  createBudget: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<ProjectBudget>>("/projects/budgets/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateBudget: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<ProjectBudget>>(`/projects/budgets/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteBudget: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/projects/budgets/${id}/`, {
      method: "DELETE",
    }),

  setBudgetStatus: (id: string, status: string) =>
    apiRequest<ApiResponse<ProjectBudget>>(`/projects/budgets/${id}/status/`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),

  wbsList: (page = 1, projectId?: string, branchId?: string, search?: string) =>
    apiRequest<ApiListResponse<WbsNode>>(
      `/projects/wbs/${qs({ page, project_id: projectId, branch_id: branchId, search })}`
    ),

  wbsTree: (projectId: string, branchId?: string) =>
    apiRequest<ApiResponse<WbsNode[]>>(`/projects/wbs/${qs({ tree: "1", project_id: projectId, branch_id: branchId })}`),

  wbsGet: (id: string) => apiRequest<ApiResponse<WbsNode>>(`/projects/wbs/${id}/`),

  wbsCreate: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<WbsNode>>("/projects/wbs/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  wbsUpdate: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<WbsNode>>(`/projects/wbs/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  wbsDelete: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/projects/wbs/${id}/`, {
      method: "DELETE",
    }),

  wbsMove: (id: string, parentId: string | null) =>
    apiRequest<ApiResponse<WbsNode>>(`/projects/wbs/${id}/move/`, {
      method: "POST",
      body: JSON.stringify({ parent_id: parentId }),
    }),

  tasks: (
    page = 1,
    filters?: { project_id?: string; status?: string; search?: string; branch_id?: string }
  ) =>
    apiRequest<ApiListResponse<ProjectTask>>(`/projects/tasks/${qs({ page, ...filters })}`),

  task: (id: string) => apiRequest<ApiResponse<ProjectTask>>(`/projects/tasks/${id}/`),

  createTask: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<ProjectTask>>("/projects/tasks/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateTask: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<ProjectTask>>(`/projects/tasks/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteTask: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/projects/tasks/${id}/`, { method: "DELETE" }),

  setTaskStatus: (id: string, status: string) =>
    apiRequest<ApiResponse<ProjectTask>>(`/projects/tasks/${id}/status/`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),

  milestones: (
    page = 1,
    filters?: { project_id?: string; status?: string; search?: string; branch_id?: string }
  ) =>
    apiRequest<ApiListResponse<ProjectMilestone>>(`/projects/milestones/${qs({ page, ...filters })}`),

  milestone: (id: string) => apiRequest<ApiResponse<ProjectMilestone>>(`/projects/milestones/${id}/`),

  createMilestone: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<ProjectMilestone>>("/projects/milestones/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateMilestone: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<ProjectMilestone>>(`/projects/milestones/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteMilestone: (id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/projects/milestones/${id}/`, { method: "DELETE" }),

  setMilestoneStatus: (id: string, status: string) =>
    apiRequest<ApiResponse<ProjectMilestone>>(`/projects/milestones/${id}/status/`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),

  construction: (kind: ConstructionKind, page = 1, projectId?: string, branchId?: string) =>
    apiRequest<ApiListResponse<ConstructionRecord>>(
      `/projects/${kind}s/${qs({ page, project_id: projectId, branch_id: branchId })}`
    ),

  constructionGet: (kind: ConstructionKind, id: string) =>
    apiRequest<ApiResponse<ConstructionRecord>>(`/projects/${kind}s/${id}/`),

  createConstruction: (kind: ConstructionKind, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<ConstructionRecord>>(`/projects/${kind}s/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  boqList: (page = 1, projectId?: string, branchId?: string) =>
    apiRequest<ApiListResponse<Boq>>(`/projects/boq/${qs({ page, project_id: projectId, branch_id: branchId })}`),

  boq: (id: string) => apiRequest<ApiResponse<Boq>>(`/projects/boq/${id}/`),

  createBoq: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Boq>>("/projects/boq/", { method: "POST", body: JSON.stringify(data) }),

  updateBoq: (id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<Boq>>(`/projects/boq/${id}/`, { method: "PATCH", body: JSON.stringify(data) }),

  setBoqStatus: (id: string, status: string) =>
    apiRequest<ApiResponse<Boq>>(`/projects/boq/${id}/status/`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),

  workers: (page = 1, projectId?: string, branchId?: string) =>
    apiRequest<ApiListResponse<ProjectWorker>>(`/projects/workers/${qs({ page, project_id: projectId, branch_id: branchId })}`),

  worker: (id: string) => apiRequest<ApiResponse<ProjectWorker>>(`/projects/workers/${id}/`),

  createWorker: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<ProjectWorker>>("/projects/workers/", { method: "POST", body: JSON.stringify(data) }),

  workerRates: (id: string) => apiRequest<ApiResponse<WorkerRate[]>>(`/projects/workers/${id}/rates/`),

  attendance: (page = 1, projectId?: string, branchId?: string) =>
    apiRequest<ApiListResponse<WorkerAttendance>>(`/projects/attendance/${qs({ page, project_id: projectId, branch_id: branchId })}`),

  createAttendance: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<WorkerAttendance>>("/projects/attendance/", { method: "POST", body: JSON.stringify(data) }),

  wages: (page = 1, projectId?: string, branchId?: string) =>
    apiRequest<ApiListResponse<DailyWage>>(`/projects/wages/${qs({ page, project_id: projectId, branch_id: branchId })}`),

  createWage: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<DailyWage>>("/projects/wages/", { method: "POST", body: JSON.stringify(data) }),

  setWageStatus: (id: string, status: string) =>
    apiRequest<ApiResponse<DailyWage>>(`/projects/wages/${id}/status/`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),

  operations: (kind: ProjectOperationKind, page = 1, projectId?: string, branchId?: string) =>
    apiRequest<ApiListResponse<ProjectOperation>>(
      `/projects/${kind}/${qs({ page, project_id: projectId, branch_id: branchId })}`
    ),

  operation: (kind: ProjectOperationKind, id: string) =>
    apiRequest<ApiResponse<ProjectOperation>>(`/projects/${kind}/${id}/`),

  createOperation: (kind: ProjectOperationKind, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<ProjectOperation>>(`/projects/${kind}/`, {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateOperation: (kind: ProjectOperationKind, id: string, data: Record<string, unknown>) =>
    apiRequest<ApiResponse<ProjectOperation>>(`/projects/${kind}/${id}/`, {
      method: "PATCH",
      body: JSON.stringify(data),
    }),

  deleteOperation: (kind: ProjectOperationKind, id: string) =>
    apiRequest<ApiResponse<Record<string, unknown>>>(`/projects/${kind}/${id}/`, { method: "DELETE" }),

  setOperationStatus: (kind: ProjectOperationKind, id: string, status: string) =>
    apiRequest<ApiResponse<ProjectOperation>>(`/projects/${kind}/${id}/status/`, {
      method: "POST",
      body: JSON.stringify({ status }),
    }),

  createMaterialRequestLine: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<ProjectOperation>>("/projects/material-request-lines/", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  inventoryAllocations: (page = 1, projectId?: string) =>
    apiRequest<ApiListResponse<ProjectInventoryAllocation>>(`/projects/inventory-allocations/${qs({ page, project_id: projectId })}`),
  createInventoryAllocation: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<ProjectInventoryAllocation>>("/projects/inventory-allocations/", {
      method: "POST", body: JSON.stringify(data),
    }),

  mobileSummary: () => apiRequest<ApiResponse<ProjectMobileSummary>>("/projects/mobile/summary/"),
  mobileTasks: () => apiRequest<ApiResponse<ProjectMobileTask[]>>("/projects/mobile/my-tasks/"),
  mobileProjects: () => apiRequest<ApiResponse<ProjectMobileProject[]>>("/projects/mobile/projects/"),
  mobileAttendance: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<WorkerAttendance>>("/projects/mobile/attendance/", { method: "POST", body: JSON.stringify(data) }),
  mobileSiteReport: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<ProjectOperation>>("/projects/mobile/site-reports/", { method: "POST", body: JSON.stringify(data) }),
  mobileSafetyIncident: (data: Record<string, unknown>) =>
    apiRequest<ApiResponse<ProjectOperation>>("/projects/mobile/safety-incidents/", { method: "POST", body: JSON.stringify(data) }),

  invoiceAccountingPreview: (id: string) =>
    apiRequest<ApiResponse<ProjectInvoiceAccountingPreview>>(`/projects/invoices/${id}/accounting-preview/`, {
      method: "POST",
    }),

  invoicePostAccounting: (id: string) =>
    apiRequest<ApiResponse<ProjectOperation>>(`/projects/invoices/${id}/post-accounting/`, {
      method: "POST",
    }),
};

export type ProjectOperationKind =
  | "material-requests"
  | "equipment"
  | "expenses"
  | "change-orders"
  | "site-reports"
  | "quality-inspections"
  | "safety-incidents"
  | "risks"
  | "issues"
  | "invoices";

export interface ProjectInventoryAllocation {
  id: string; project_id: string; wbs_node_id: string | null; product_id: string;
  quantity: number; unit_cost: number; allocated_at: string; source_type: "manual" | "grn" | "material_request";
  source_id: string | null; notes: string;
}
export interface ProjectMobileSummary { active_projects: number; my_open_tasks: number; today: string; }
export interface ProjectMobileTask { id: string; project_id: string; title: string; status: string; priority: string; planned_end: string | null; }
export interface ProjectMobileProject { id: string; project_code: string; name: string; status: string; progress_percent: number; }

export interface ProjectOperation {
  id: string;
  project_id: string;
  status?: string;
  code?: string;
  name?: string;
  title?: string;
  description?: string;
  notes?: string;
  amount?: number;
  total_amount?: number;
  amount_delta?: number;
  created_at?: string | null;
  [key: string]: unknown;
}

export interface ProjectInvoiceAccountingPreview {
  source: string;
  invoice_id: string;
  currency: string;
  note: string;
  already_posted?: boolean;
  journal_entry_id?: string | null;
  lines: Array<{
    account_code: string;
    account_name?: string;
    account_id?: string;
    debit: number;
    credit: number;
    description: string;
  }>;
}

export interface ProjectBudgetLine {
  id?: string;
  category: string;
  description: string;
  planned_amount: number;
  committed_amount?: number;
  actual_amount?: number;
  variance?: number;
  sort_order?: number;
  notes?: string;
}

export interface ProjectBudget {
  id: string;
  project_id: string;
  project_code: string;
  project_name: string;
  version: number;
  name: string;
  status: string;
  currency: string;
  total_planned: number;
  total_committed: number;
  total_actual: number;
  variance: number;
  notes: string;
  is_active: boolean;
  approved_at: string | null;
  lines: ProjectBudgetLine[];
  created_at: string | null;
  updated_at: string | null;
}

export interface ProjectTask {
  id: string;
  project_id: string;
  project_code: string;
  project_name: string;
  wbs_node_id: string | null;
  wbs_code: string;
  wbs_name: string;
  assignee_id: string | null;
  assignee_name: string;
  task_code: string;
  title: string;
  description: string;
  priority: string;
  status: string;
  planned_start: string | null;
  planned_end: string | null;
  actual_start: string | null;
  actual_end: string | null;
  progress_percent: number;
  estimated_hours: number;
  actual_hours: number;
  sort_order: number;
  notes: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface ProjectMilestone {
  id: string;
  project_id: string;
  project_code: string;
  project_name: string;
  wbs_node_id: string | null;
  wbs_code: string;
  wbs_name: string;
  code: string;
  name: string;
  description: string;
  due_date: string | null;
  completed_at: string | null;
  status: string;
  is_critical: boolean;
  sort_order: number;
  notes: string;
  created_at: string | null;
  updated_at: string | null;
}

export type ConstructionKind = "site" | "building" | "floor" | "unit";

export interface ConstructionRecord {
  id: string;
  project_id: string;
  code: string;
  name: string;
  notes: string;
  address?: string;
  location?: string;
  status?: string;
  floors_count?: number;
  level_number?: number;
  unit_type?: string;
  area_sqm?: number;
  site_id?: string | null;
  building_id?: string | null;
  floor_id?: string | null;
}

export interface BoqLine {
  id?: string;
  item_code: string;
  description: string;
  unit_of_measure: string;
  quantity: number;
  unit_rate: number;
  amount?: number;
  category: string;
  sort_order?: number;
  wbs_node_id?: string | null;
  unit_id?: string | null;
  notes?: string;
}

export interface Boq {
  id: string;
  project_id: string;
  version: number;
  name: string;
  status: string;
  currency: string;
  total_amount: number;
  notes: string;
  is_active: boolean;
  approved_at: string | null;
  lines: BoqLine[];
}

export interface ProjectWorker {
  id: string;
  project_id: string;
  code: string;
  full_name: string;
  worker_type: string;
  phone: string;
  trade: string;
  daily_rate: number;
  is_active: boolean;
  employee_user_id: string | null;
  notes: string;
}

export interface WorkerRate {
  id: string;
  rate: number;
  effective_from: string;
  effective_to: string | null;
  notes: string;
}

export interface WorkerAttendance {
  id: string;
  project_id: string;
  worker_id: string;
  work_date: string;
  hours_worked: number;
  status: string;
  rate_applied: number;
  wbs_node_id: string | null;
  task_id: string | null;
  notes: string;
}

export interface DailyWage {
  id: string;
  project_id: string;
  worker_id: string;
  attendance_id: string | null;
  work_date: string;
  hours: number;
  rate: number;
  amount: number;
  status: string;
  notes: string;
}
