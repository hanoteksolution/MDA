import { describe, expect, it } from "vitest";
import { isElevatedUser, postLoginPath, shouldShowModuleHub } from "./postLogin";
import type { User } from "@/types/models";

function user(partial: Partial<User> = {}): User {
  return {
    id: "1",
    username: "u",
    email: "",
    first_name: "U",
    last_name: "Ser",
    role: null,
    branch: null,
    is_super_admin: false,
    is_platform_admin: false,
    is_superuser: false,
    permissions: [],
    enabled_modules: [],
    ...partial,
  };
}

describe("isElevatedUser", () => {
  it("exempts Superadmin / Platform Admin from the subscription gate", () => {
    expect(isElevatedUser(user({ is_super_admin: true }))).toBe(true);
    expect(isElevatedUser(user({ is_platform_admin: true }))).toBe(true);
    expect(isElevatedUser(user({ is_superuser: true }))).toBe(true);
    expect(isElevatedUser(user({ role: { id: "r1", name: "Super Admin", slug: "super_admin" } }))).toBe(
      true
    );
  });

  it("never exempts a regular tenant admin from the subscription gate", () => {
    expect(isElevatedUser(user({ role: { id: "r2", name: "Admin", slug: "admin" } }))).toBe(false);
    expect(isElevatedUser(user())).toBe(false);
    expect(isElevatedUser(null)).toBe(false);
  });
});

describe("postLoginPath", () => {
  it("sends elevated admins to the hub", () => {
    expect(postLoginPath(user({ is_super_admin: true }))).toBe("/modules");
  });

  it("sends multi-industry users to the hub", () => {
    expect(
      postLoginPath(
        user({
          enabled_modules: ["gym", "restaurant"],
          permissions: ["gym.view", "restaurant.view"],
        })
      )
    ).toBe("/modules");
  });

  it("sends a single gym user to gym", () => {
    expect(
      postLoginPath(
        user({
          enabled_modules: ["gym"],
          permissions: ["gym.view"],
        })
      )
    ).toBe("/gym");
  });

  it("sends engine-only users to the retail workspace", () => {
    expect(postLoginPath(user({ enabled_modules: ["sales"], permissions: ["sales.view"] }))).toBe(
      "/retail/sales"
    );
  });

  it("sends cashiers on multi-venue shops to retail POS", () => {
    expect(
      postLoginPath(
        user({
          enabled_modules: ["gym", "restaurant", "pos", "sales", "inventory"],
          permissions: ["pos.access", "sales.view", "products.view"],
          first_name: "POS",
          last_name: "Only",
        })
      )
    ).toBe("/retail/pos");
  });

  it("sends inventory staff on multi-venue shops to retail inventory", () => {
    expect(
      postLoginPath(
        user({
          enabled_modules: ["gym", "restaurant", "pos", "sales", "inventory"],
          permissions: ["dashboard.view", "inventory.view", "products.view", "reports.view"],
        })
      )
    ).toBe("/retail/inventory");
  });

  it("does not prefer reports over inventory for inventory staff", () => {
    expect(
      postLoginPath(
        user({
          enabled_modules: ["gym", "inventory", "pos"],
          permissions: ["inventory.view", "products.view", "reports.view", "dashboard.view"],
        })
      )
    ).toBe("/retail/inventory");
  });

  it("falls back to dashboard when no workspaces are visible", () => {
    expect(postLoginPath(user({ enabled_modules: [], permissions: [] }))).toBe("/dashboard");
  });
});

describe("shouldShowModuleHub", () => {
  it("is true for super admin", () => {
    expect(shouldShowModuleHub(user({ is_super_admin: true }))).toBe(true);
  });
});
