import { create } from "zustand";
import {
  ALL_BRANCHES,
  clearActiveBranchId,
  getActiveBranchId,
  setActiveBranchId,
} from "@/services/api/branchContext";
import { organizationApi, type BranchSummary } from "@/services/api/organization";

/**
 * Global branch context for the whole workspace (POS, inventory, sales, purchases,
 * finance, reports, notifications all read from here).
 *
 * The store holds only branches the backend says this user may act in. Selecting
 * anything else is refused locally *and* would be refused by the API — the backend
 * is authoritative, this is a usability guard, not the security boundary.
 */

export interface BranchState {
  branches: BranchSummary[];
  /** True when the user may select the consolidated "All branches" view. */
  coversAll: boolean;
  activeBranchId: string | null;
  loading: boolean;
  loaded: boolean;
  error: string | null;
  /** Bumps whenever the active branch changes, so screens can refetch. */
  scopeVersion: number;

  loadBranches: () => Promise<void>;
  setActiveBranch: (branchId: string | null) => boolean;
  selectAllBranches: () => void;
  reset: () => void;
  activeBranch: () => BranchSummary | null;
  canInBranch: (permission: string, branchId?: string | null) => boolean;
}

export const useBranchStore = create<BranchState>((set, get) => ({
  branches: [],
  coversAll: false,
  activeBranchId: getActiveBranchId(),
  loading: false,
  loaded: false,
  error: null,
  scopeVersion: 0,

  async loadBranches() {
    set({ loading: true, error: null });
    try {
      const response = await organizationApi.myBranches();
      const branches = response.data.branches ?? [];
      const coversAll = Boolean(response.data.covers_all);
      const current = get().activeBranchId;
      const stillValid =
        (current === ALL_BRANCHES && coversAll) || branches.some((b) => b.id === current);
      const next = stillValid
        ? current
        : response.data.default_branch_id ?? branches[0]?.id ?? null;

      if (next !== current) setActiveBranchId(next);
      set((state) => ({
        branches,
        coversAll,
        activeBranchId: next,
        loading: false,
        loaded: true,
        scopeVersion: next === current ? state.scopeVersion : state.scopeVersion + 1,
      }));
    } catch (error) {
      set({
        loading: false,
        loaded: true,
        error: error instanceof Error ? error.message : "Could not load branches.",
      });
    }
  },

  setActiveBranch(branchId) {
    if (branchId === null) {
      clearActiveBranchId();
      set((state) => ({ activeBranchId: null, scopeVersion: state.scopeVersion + 1 }));
      return true;
    }
    if (branchId === ALL_BRANCHES && !get().coversAll) {
      set({ error: "You do not have access to every branch." });
      return false;
    }
    if (branchId !== ALL_BRANCHES && !get().branches.some((b) => b.id === branchId)) {
      // A branch the user has no access to never enters the store.
      set({ error: "You do not have access to that branch." });
      return false;
    }
    if (branchId === get().activeBranchId) return true;
    setActiveBranchId(branchId);
    set((state) => ({
      activeBranchId: branchId,
      error: null,
      scopeVersion: state.scopeVersion + 1,
    }));
    return true;
  },

  selectAllBranches() {
    get().setActiveBranch(ALL_BRANCHES);
  },

  reset() {
    clearActiveBranchId();
    set({
      branches: [],
      coversAll: false,
      activeBranchId: null,
      loading: false,
      loaded: false,
      error: null,
      scopeVersion: 0,
    });
  },

  activeBranch() {
    const { branches, activeBranchId } = get();
    if (!activeBranchId || activeBranchId === ALL_BRANCHES) return null;
    return branches.find((b) => b.id === activeBranchId) ?? null;
  },

  canInBranch(permission, branchId) {
    const { branches, activeBranchId } = get();
    const target = branchId ?? activeBranchId;
    if (!target || target === ALL_BRANCHES) {
      return branches.some((b) => b.permissions.includes(permission));
    }
    const branch = branches.find((b) => b.id === target);
    return Boolean(branch?.permissions.includes(permission));
  },
}));
