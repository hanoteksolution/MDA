import type { BranchOverviewRow } from "@/services/api/branchOps";
import type { BranchDetail } from "@/types/models/admin";

/**
 * Branches that belong to the given company. Falls back to the full list when either side of
 * the relationship is unknown, since most tenants have exactly one company and `list_branches`
 * already scopes non-elevated users to it — this is a defensive narrowing for elevated users who
 * can see more than one company's branches, not the primary access control.
 */
export function branchesForCompany(branches: BranchDetail[], companyId?: string | null): BranchDetail[] {
  if (!companyId) return branches;
  const known = branches.filter((b) => b.company_id);
  if (known.length === 0) return branches;
  return branches.filter((b) => !b.company_id || b.company_id === companyId);
}

/** Warehouse/POS-terminal counts and manager names for one branch, from the branch-overview report. */
export function overviewFor(overview: BranchOverviewRow[], branchId: string): BranchOverviewRow | undefined {
  return overview.find((r) => r.branch_id === branchId);
}
