import { describe, expect, it } from "vitest";
import { postLoginPath, shouldShowModuleHub } from "./postLogin";
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
      "/retail"
    );
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
