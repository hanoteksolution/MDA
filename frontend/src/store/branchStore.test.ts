/** FE-2: the branch switcher never holds a branch the backend did not grant. */
import { beforeEach, describe, expect, it, vi } from "vitest";

// Vitest runs in the "node" environment here, so provide the storage the store uses.
if (typeof globalThis.localStorage === "undefined") {
  const store = new Map<string, string>();
  Object.defineProperty(globalThis, "localStorage", {
    value: {
      getItem: (k: string) => (store.has(k) ? store.get(k)! : null),
      setItem: (k: string, v: string) => void store.set(k, String(v)),
      removeItem: (k: string) => void store.delete(k),
      clear: () => store.clear(),
      key: (i: number) => Array.from(store.keys())[i] ?? null,
      get length() {
        return store.size;
      },
    },
    configurable: true,
  });
}

const myBranches = vi.fn();

vi.mock("@/services/api/organization", () => ({
  organizationApi: {
    myBranches: () => myBranches(),
  },
}));

import { ALL_BRANCHES, getActiveBranchId } from "@/services/api/branchContext";
import { useBranchStore } from "@/store/branchStore";

const HODAN = {
  id: "11111111-1111-1111-1111-111111111111",
  name: "Hodan",
  code: "HODAN",
  branch_type: "RETAIL",
  status: "ACTIVE",
  is_default: true,
  is_manager: false,
  permissions: ["pos.access", "sales.create", "inventory.view"],
};
const BAKAARO = {
  id: "22222222-2222-2222-2222-222222222222",
  name: "Bakaaro",
  code: "BAKAARO",
  branch_type: "RETAIL",
  status: "ACTIVE",
  is_default: false,
  is_manager: false,
  permissions: ["inventory.view"],
};
const FORBIDDEN_ID = "99999999-9999-9999-9999-999999999999";

function respond(branches = [HODAN, BAKAARO], defaultId: string | null = HODAN.id, coversAll = true) {
  myBranches.mockResolvedValue({
    data: { branches, default_branch_id: defaultId, count: branches.length, covers_all: coversAll },
  });
}

describe("branchStore", () => {
  beforeEach(() => {
    localStorage.clear();
    myBranches.mockReset();
    useBranchStore.getState().reset();
  });

  it("loads only the branches the backend returned", async () => {
    respond();
    await useBranchStore.getState().loadBranches();
    expect(useBranchStore.getState().branches.map((b) => b.code)).toEqual(["HODAN", "BAKAARO"]);
    expect(useBranchStore.getState().loaded).toBe(true);
  });

  it("selects the backend default branch on first load", async () => {
    respond();
    await useBranchStore.getState().loadBranches();
    expect(useBranchStore.getState().activeBranchId).toBe(HODAN.id);
    expect(getActiveBranchId()).toBe(HODAN.id);
  });

  it("refuses a branch id that is not in the accessible list", async () => {
    respond();
    await useBranchStore.getState().loadBranches();

    const accepted = useBranchStore.getState().setActiveBranch(FORBIDDEN_ID);

    expect(accepted).toBe(false);
    expect(useBranchStore.getState().activeBranchId).toBe(HODAN.id);
    expect(getActiveBranchId()).toBe(HODAN.id);
    expect(useBranchStore.getState().error).toMatch(/do not have access/i);
  });

  it("bumps scopeVersion when the branch changes so screens refetch", async () => {
    respond();
    await useBranchStore.getState().loadBranches();
    const before = useBranchStore.getState().scopeVersion;

    useBranchStore.getState().setActiveBranch(BAKAARO.id);

    expect(useBranchStore.getState().activeBranchId).toBe(BAKAARO.id);
    expect(useBranchStore.getState().scopeVersion).toBe(before + 1);
  });

  it("does not bump scopeVersion when the same branch is reselected", async () => {
    respond();
    await useBranchStore.getState().loadBranches();
    const before = useBranchStore.getState().scopeVersion;
    useBranchStore.getState().setActiveBranch(HODAN.id);
    expect(useBranchStore.getState().scopeVersion).toBe(before);
  });

  it("drops a stored branch that the user no longer has access to", async () => {
    localStorage.setItem("active_branch_id", FORBIDDEN_ID);
    useBranchStore.setState({ activeBranchId: FORBIDDEN_ID });
    respond();

    await useBranchStore.getState().loadBranches();

    expect(useBranchStore.getState().activeBranchId).toBe(HODAN.id);
    expect(getActiveBranchId()).toBe(HODAN.id);
  });

  it("keeps a stored branch that is still accessible", async () => {
    localStorage.setItem("active_branch_id", BAKAARO.id);
    useBranchStore.setState({ activeBranchId: BAKAARO.id });
    respond();

    await useBranchStore.getState().loadBranches();

    expect(useBranchStore.getState().activeBranchId).toBe(BAKAARO.id);
  });

  it("reports per-branch permissions, not a single global set", async () => {
    respond();
    await useBranchStore.getState().loadBranches();
    const store = useBranchStore.getState();

    expect(store.canInBranch("pos.access", HODAN.id)).toBe(true);
    expect(store.canInBranch("pos.access", BAKAARO.id)).toBe(false);
    expect(store.canInBranch("inventory.view", BAKAARO.id)).toBe(true);
    expect(store.canInBranch("pos.access", FORBIDDEN_ID)).toBe(false);
  });

  it("allows the 'all branches' selector for reporting views", async () => {
    respond();
    await useBranchStore.getState().loadBranches();
    useBranchStore.getState().selectAllBranches();
    expect(useBranchStore.getState().activeBranchId).toBe(ALL_BRANCHES);
    expect(useBranchStore.getState().activeBranch()).toBeNull();
  });

  it("refuses 'all branches' when the user cannot see every branch of the tenant", async () => {
    respond([HODAN, BAKAARO], HODAN.id, false);
    await useBranchStore.getState().loadBranches();
    expect(useBranchStore.getState().setActiveBranch(ALL_BRANCHES)).toBe(false);
    expect(useBranchStore.getState().activeBranchId).toBe(HODAN.id);
  });

  it("handles a user with no branches without selecting one", async () => {
    respond([], null);
    await useBranchStore.getState().loadBranches();
    expect(useBranchStore.getState().branches).toEqual([]);
    expect(useBranchStore.getState().activeBranchId).toBeNull();
  });

  it("surfaces a load failure instead of silently showing stale branches", async () => {
    myBranches.mockRejectedValue(new Error("network down"));
    await useBranchStore.getState().loadBranches();
    expect(useBranchStore.getState().error).toBe("network down");
    expect(useBranchStore.getState().branches).toEqual([]);
  });

  it("clears the branch on reset (logout)", async () => {
    respond();
    await useBranchStore.getState().loadBranches();
    useBranchStore.getState().reset();
    expect(useBranchStore.getState().activeBranchId).toBeNull();
    expect(getActiveBranchId()).toBeNull();
  });
});
