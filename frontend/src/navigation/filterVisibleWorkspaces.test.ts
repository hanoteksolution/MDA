import { describe, expect, it } from "vitest";
import { filterVisibleWorkspaces, resolveHospitalityProfile } from "./moduleWorkspaces";

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

  it("includes restaurant for elevated users and cafeteria shell", () => {
    const cards = filterVisibleWorkspaces([], {
      elevated: true,
      includeFinance: true,
    });
    expect(cards.some((c) => c.code === "restaurant")).toBe(true);
    expect(cards.some((c) => c.code === "cafeteria")).toBe(true);
    expect(cards.some((c) => c.code === "gym")).toBe(true);
    expect(cards.some((c) => c.code === "finance")).toBe(true);
  });

  it("shows cafeteria and hides restaurant for cafeteria business type", () => {
    const cards = filterVisibleWorkspaces(["pos", "sales", "inventory", "restaurant"], {
      elevated: false,
      hasPermission: () => true,
      businessTypeCode: "cafeteria",
    });
    expect(cards.some((c) => c.code === "cafeteria")).toBe(true);
    expect(cards.some((c) => c.code === "restaurant")).toBe(false);
  });

  it("shows restaurant and hides cafeteria for restaurant business type", () => {
    const cards = filterVisibleWorkspaces(["pos", "sales", "inventory", "restaurant"], {
      elevated: false,
      hasPermission: () => true,
      businessTypeCode: "restaurant",
    });
    expect(cards.some((c) => c.code === "restaurant")).toBe(true);
    expect(cards.some((c) => c.code === "cafeteria")).toBe(false);
  });
});

describe("resolveHospitalityProfile", () => {
  it("maps cafeteria business types", () => {
    expect(resolveHospitalityProfile("cafeteria")).toBe("cafeteria");
    expect(resolveHospitalityProfile("gym_cafeteria")).toBe("cafeteria");
  });

  it("defaults to restaurant for other types", () => {
    expect(resolveHospitalityProfile("hotel")).toBe("restaurant");
    expect(resolveHospitalityProfile("gym")).toBe("restaurant");
  });
});
