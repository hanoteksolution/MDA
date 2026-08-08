import { describe, expect, it } from "vitest";
import { filterVisibleWorkspaces } from "./moduleWorkspaces";

describe("filterVisibleWorkspaces", () => {
  it("hides capability engines from the hub", () => {
    const cards = filterVisibleWorkspaces(["pos", "sales", "gym"], {
      elevated: false,
      hasPermission: () => true,
      includeFinance: true,
    });
    expect(cards.some((c) => c.kind === "capability")).toBe(false);
    expect(cards.some((c) => c.code === "gym")).toBe(true);
  });

  it("includes all industry cards for elevated users", () => {
    const cards = filterVisibleWorkspaces([], {
      elevated: true,
      includeFinance: true,
    });
    expect(cards.some((c) => c.code === "restaurant")).toBe(true);
    expect(cards.some((c) => c.code === "gym")).toBe(true);
    expect(cards.some((c) => c.code === "finance")).toBe(true);
  });
});
