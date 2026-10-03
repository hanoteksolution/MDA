import { describe, expect, it, vi } from "vitest";

vi.hoisted(() => {
  const values = new Map<string, string>();
  Object.assign(globalThis, { localStorage: { getItem: (k: string) => values.get(k) ?? null, setItem: (k: string, v: string) => void values.set(k, v), removeItem: (k: string) => void values.delete(k), clear: () => values.clear() } });
});
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import type { BranchReport } from "@/services/api/branchOps";
import type { ProductAvailability } from "@/types/models/catalog";
import { activeBranchLabel } from "@/components/branch/BranchSwitcher";
import { branchSwitchWarning, discardBranchBoundWork, setBranchSwitchGuard } from "@/components/branch/branchSwitchGuard";
import { overviewNavSections } from "@/navigation/businessWorkspaces";
import { availableTransferActions } from "./lib";
import { BranchReportTable, ReconcileBadge } from "./components/BranchReportTable";
import { CrossBranchPanel } from "./components/CrossBranchPanel";
import { SendStockDialog, sendStockGate } from "./components/SendStockDialog";

const html = (el: React.ReactElement) => renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);
const HODAN = "h", BAKAARO = "b";

const availability: ProductAvailability = {
  product_id: "p1", product_sku: "IP17PRO", product_name: "iPhone 17 Pro",
  current_branch: { branch_id: HODAN, branch_name: "Hodan", on_hand: 0, reserved: 0, available: 0, in_transit: 0, warehouses: [] },
  other_branches: [
    { branch_id: BAKAARO, branch_name: "Bakaaro", branch_code: "BAKAARO", on_hand: 12, reserved: 0, available: 12, in_transit: 0, warehouses: null },
    { branch_id: "k", branch_name: "KM4", branch_code: "KM4", on_hand: "4.0000" as unknown as number, reserved: 4, available: 0, in_transit: 0,
      warehouses: [{ warehouse_id: "w", warehouse_name: "KM4 WH", on_hand: 4, reserved: 4, available: 0 }] },
  ],
  open_transfers: [{ id: "t", request_number: "BTR-000001", status: "REQUESTED", source_branch_name: "Bakaaro", destination_branch_name: "Hodan", quantity_requested: "3", direction: "incoming" }],
};

describe("cross-branch availability", () => {
  it("shows the local shortage and each branch's stock without summing them into the local figure", () => {
    const out = html(<CrossBranchPanel data={availability} requested={2} onRequestTransfer={() => undefined} />);
    expect(out).toContain("Hodan (this branch)");
    expect(out).toContain(">0 available<");
    expect(out).toContain("Local shortage: 2 short of 2.");
    expect(out).toContain(">Bakaaro<");
    expect(out).toContain(">12<");
    expect(out).toContain("KM4 WH: 0 available"); // warehouse detail only where permitted
    expect(out).toContain("BTR-000001");
    // Transfer can be requested only from a branch that has stock.
    expect(out.match(/Request transfer/g)?.length).toBe(1);
    expect(out).not.toContain("16");
  });

  it("explains when the role cannot see other branches", () => {
    const out = html(<CrossBranchPanel data={{ ...availability, other_branches: [] }} />);
    expect(out).toContain("cannot see other branches");
    expect(out).not.toContain("Request transfer");
  });
});

describe("transfer workflow actions", () => {
  const t = { source_branch_id: BAKAARO, destination_branch_id: HODAN };
  const onlyHodan = (_p: string, b: string) => b === HODAN;
  const onlyBakaaro = (_p: string, b: string) => b === BAKAARO;
  it("gives approval/reservation/dispatch to the source branch only", () => {
    // The requesting destination may only cancel before dispatch.
    expect(availableTransferActions({ ...t, status: "REQUESTED" }, onlyHodan).map((a) => a.action)).toEqual(["cancel"]);
    expect(availableTransferActions({ ...t, status: "RESERVED" }, onlyHodan).map((a) => a.action)).toEqual(["cancel"]);
    expect(availableTransferActions({ ...t, status: "IN_TRANSIT" }, onlyHodan).map((a) => a.action)).not.toContain("cancel");
    expect(availableTransferActions({ ...t, status: "REQUESTED" }, () => false)).toEqual([]);
    expect(availableTransferActions({ ...t, status: "REQUESTED" }, onlyBakaaro).map((a) => a.action)).toEqual(["approve", "reject", "cancel"]);
    expect(availableTransferActions({ ...t, status: "RESERVED" }, onlyBakaaro).map((a) => a.action)).toEqual(["dispatch", "cancel"]);
  });
  it("gives receiving and completion to the destination branch only", () => {
    expect(availableTransferActions({ ...t, status: "IN_TRANSIT" }, onlyHodan).map((a) => a.action)).toEqual(["receive"]);
    expect(availableTransferActions({ ...t, status: "IN_TRANSIT" }, onlyBakaaro)).toEqual([]);
    expect(availableTransferActions({ ...t, status: "RECEIVED" }, onlyHodan).map((a) => a.action)).toEqual(["complete"]);
    expect(availableTransferActions({ ...t, status: "COMPLETED" }, () => true)).toEqual([]);
  });
});

describe("branch reports", () => {
  const report: BranchReport = {
    report: "sales", mode: "consolidated", date_from: null, date_to: null, reconciles: true,
    branches: [
      { branch_id: HODAN, branch_code: "HODAN", branch_name: "Hodan", invoices: 0, gross: 0, refunded: 0, net: 0 },
      { branch_id: BAKAARO, branch_code: "BAKAARO", branch_name: "Bakaaro", invoices: 2, gross: 2400, refunded: 0, net: 2400 },
    ],
    consolidated: { invoices: 2, gross: 2400, refunded: 0, net: 2400 },
  };
  it("renders branch rows plus the server's company total, never a client-side sum", () => {
    const out = html(<BranchReportTable report={{ ...report, consolidated: { ...report.consolidated, net: 9999 } }} />);
    expect(out).toContain("Company total");
    expect(out).toContain("9,999.00"); // shows the backend figure verbatim
  });
  it("flags reconciliation state", () => {
    expect(html(<ReconcileBadge report={report} />)).toContain("reconcile with company total");
    expect(html(<ReconcileBadge report={{ reconciles: false }} />)).toContain("do not reconcile");
  });
  it("hides the company total for a single-branch report", () => {
    expect(html(<BranchReportTable report={{ ...report, mode: "single", branches: [report.branches[1]] }} />)).not.toContain("Company total");
  });
});

describe("branch switching", () => {
  it("labels the active scope", () => {
    const branches = [{ id: HODAN, name: "Hodan" }];
    expect(activeBranchLabel("all", branches)).toBe("All branches");
    expect(activeBranchLabel(HODAN, branches)).toBe("Hodan");
    expect(activeBranchLabel(null, branches, "Main")).toBe("Main");
  });
  it("asks before discarding branch-bound work, and discards it on confirm", () => {
    const discard = vi.fn();
    setBranchSwitchGuard({ warning: () => "The cart has 2 line(s) for Hodan.", discard });
    expect(branchSwitchWarning()).toContain("Hodan");
    discardBranchBoundWork();
    expect(discard).toHaveBeenCalledOnce();
    setBranchSwitchGuard(null);
    expect(branchSwitchWarning()).toBeNull();
  });
  it("shows branch navigation by permission", () => {
    const links = (has: string[]) => overviewNavSections([], { hasPermission: (c: string) => has.includes(c) }).flatMap((s) => s.items.map((i) => i.to));
    expect(links(["reports.view", "inventory.transfer"])).toEqual(expect.arrayContaining(["/branches", "/branches/transfers"]));
    expect(links(["pos.access"])).not.toContain("/branches");
  });
});

describe("send stock to branch", () => {
  const can = (perms: Record<string, string[]>) => (p: string, b?: string | null) => Boolean(b && perms[b]?.includes(p));
  it("needs a single sending branch where the user may transfer", () => {
    expect(sendStockGate("all", can({})).canSend).toBe(false);
    expect(sendStockGate(null, can({})).reason).toContain("Select the sending branch");
    expect(sendStockGate(BAKAARO, can({ [BAKAARO]: ["inventory.view"] })).reason).toContain("cannot send stock");
    expect(sendStockGate(BAKAARO, can({ [BAKAARO]: ["inventory.transfer"] }))).toEqual({ source: BAKAARO, canSend: true, reason: "" });
  });
  it("explains itself instead of opening a form when no branch is selected", () => {
    expect(html(<SendStockDialog open onClose={() => undefined} />)).toContain("Select the sending branch");
  });
});
