import { apiRequest } from "@/services/api/http";

export interface BranchSummary {
  id: string;
  name: string;
  code: string;
  branch_type: string;
  status: string;
  is_default: boolean;
  is_manager: boolean;
  permissions: string[];
}

export interface MyBranchesResponse {
  data: {
    branches: BranchSummary[];
    default_branch_id: string | null;
    count: number;
  };
}

export interface BranchContextResponse {
  data: {
    branch_ids: string[];
    branch_id: string | null;
    is_all: boolean;
    requested_all: boolean;
    unscoped: boolean;
  };
}

export const organizationApi = {
  myBranches: () => apiRequest<MyBranchesResponse>("/organization/my-branches/"),
  branchContext: () => apiRequest<BranchContextResponse>("/organization/context/"),
  stockLocations: (params?: { warehouse?: string }) =>
    apiRequest<{ data: unknown[] }>(
      `/organization/stock-locations/${params?.warehouse ? `?warehouse=${params.warehouse}` : ""}`
    ),
  posTerminals: () => apiRequest<{ data: unknown[] }>("/organization/pos-terminals/"),
  cashRegisters: () => apiRequest<{ data: unknown[] }>("/organization/cash-registers/"),
  branchAccess: () => apiRequest<{ data: unknown[] }>("/organization/branch-access/"),
  accessProfiles: () => apiRequest<{ data: unknown[] }>("/organization/access-profiles/"),
};
