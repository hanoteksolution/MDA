import { describe, expect, it, vi } from "vitest";

vi.hoisted(() => {
  const values = new Map<string, string>();
  Object.assign(globalThis, { localStorage: { getItem: (k: string) => values.get(k) ?? null, setItem: (k: string, v: string) => void values.set(k, v), removeItem: (k: string) => void values.delete(k), clear: () => values.clear() } });
});
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import type { BranchDetail } from "@/types/models/admin";
import type { BranchOverviewRow } from "@/services/api/branchOps";
import { branchesForCompany, overviewFor } from "./lib";
import { CompanyBranchesSection } from "./pages/SettingsPage";

const html = (el: React.ReactElement) => renderToStaticMarkup(<MemoryRouter>{el}</MemoryRouter>);

const branch = (over: Partial<BranchDetail>): BranchDetail => ({
  id: "b1", name: "Bakaaro", code: "BAKAARO", address: "", phone: "", email: "",
  is_active: true, is_default: false, created_at: "", updated_at: "", ...over,
});

describe("branchesForCompany", () => {
  it("keeps only branches belonging to the given company", () => {
    const branches = [
      branch({ id: "b1", company_id: "c1" }),
      branch({ id: "b2", company_id: "c2" }),
    ];
    expect(branchesForCompany(branches, "c1").map((b) => b.id)).toEqual(["b1"]);
  });

  it("falls back to the full list when the company or the branch rows carry no company id", () => {
    const branches = [branch({ id: "b1" }), branch({ id: "b2" })];
    expect(branchesForCompany(branches, "c1")).toHaveLength(2);
    expect(branchesForCompany(branches, null)).toHaveLength(2);
  });
});

describe("overviewFor", () => {
  it("finds the overview row for a branch id", () => {
    const overview: BranchOverviewRow[] = [
      { branch_id: "b1", code: "BAKAARO", name: "Bakaaro", status: "ACTIVE", is_active: true, is_default: true,
        branch_type: "RETAIL", phone: "", address: "", company_id: "c1", company_name: "AM Electronics",
        managers: ["Amina"], users: 2, warehouses: 1, pos_terminals: 2, cash_registers: 2, open_shifts: 1,
        sales_net: 0, sales_invoices: 0, stock_value: 0, low_stock: 0, out_of_stock: 0,
        transfers_open: 0, transfers_awaiting_approval: 0 },
    ];
    expect(overviewFor(overview, "b1")?.managers).toEqual(["Amina"]);
    expect(overviewFor(overview, "missing")).toBeUndefined();
  });
});

describe("CompanyBranchesSection", () => {
  it("shows the branch count, its branches and cheap structure counts under the company name", () => {
    const branches = [branch({ id: "b1", name: "Bakaaro", code: "BAKAARO", address: "Airport Rd", company_id: "c1" })];
    const overview: BranchOverviewRow[] = [
      { branch_id: "b1", code: "BAKAARO", name: "Bakaaro", status: "ACTIVE", is_active: true, is_default: false,
        branch_type: "RETAIL", phone: "", address: "Airport Rd", company_id: "c1", company_name: "AM Electronics",
        managers: ["Amina"], users: 1, warehouses: 1, pos_terminals: 2, cash_registers: 1, open_shifts: 0,
        sales_net: 0, sales_invoices: 0, stock_value: 0, low_stock: 0, out_of_stock: 0,
        transfers_open: 0, transfers_awaiting_approval: 0 },
    ];
    const out = html(<CompanyBranchesSection companyName="AM Electronics" branches={branches} overview={overview} onAddBranch={() => undefined} />);
    expect(out).toContain("1 branch operate"); // pluralization: singular count
    expect(out).toContain("AM Electronics");
    expect(out).toContain("Bakaaro");
    expect(out).toContain("Airport Rd");
    expect(out).toContain("Amina");
    expect(out).toContain("View");
  });

  it("shows an empty state instead of an empty grid when the shop has no branches", () => {
    const out = html(<CompanyBranchesSection companyName="AM Electronics" branches={[]} overview={[]} onAddBranch={() => undefined} />);
    expect(out).toContain("No branches yet");
  });
});
