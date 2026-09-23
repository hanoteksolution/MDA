/**
 * Active branch for outgoing API calls.
 *
 * Kept in a plain module (not the Zustand store) so `http.ts` can read it without
 * importing the store, which would create a cycle. The value is a *hint* only: the
 * backend re-checks every branch id against the caller's real access, so a tampered
 * value here can never widen what the API returns.
 */

const STORAGE_KEY = "active_branch_id";

export const ALL_BRANCHES = "all";

let activeBranchId: string | null = null;

function readStored(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function getActiveBranchId(): string | null {
  if (activeBranchId === null) activeBranchId = readStored();
  return activeBranchId;
}

export function setActiveBranchId(branchId: string | null): void {
  activeBranchId = branchId;
  try {
    if (branchId) localStorage.setItem(STORAGE_KEY, branchId);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Private mode / blocked storage: the in-memory value still works this session.
  }
}

export function clearActiveBranchId(): void {
  setActiveBranchId(null);
}

/** Header sent with every authenticated request while a branch is selected. */
export function branchHeaders(): Record<string, string> {
  const id = getActiveBranchId();
  return id ? { "X-Branch-Id": id } : {};
}
