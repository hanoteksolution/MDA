import { describe, expect, it } from "vitest";
import { tabFromWorkspacePath } from "./useWorkspaceTab";

const GYM_TABS = {
  members: "members",
  memberships: "subscriptions",
  attendance: "attendance",
  classes: "classes",
} as const;

describe("tabFromWorkspacePath", () => {
  it("uses the default tab on the workspace root", () => {
    expect(tabFromWorkspacePath("/gym", "/gym", GYM_TABS, "members")).toBe("members");
    expect(tabFromWorkspacePath("/gym/dashboard", "/gym", GYM_TABS, "members")).toBe("members");
  });

  it("maps feature suffixes to tabs", () => {
    expect(tabFromWorkspacePath("/gym/classes", "/gym", GYM_TABS, "members")).toBe("classes");
    expect(tabFromWorkspacePath("/gym/memberships", "/gym", GYM_TABS, "members")).toBe(
      "subscriptions"
    );
  });

  it("falls back to default for unknown suffixes", () => {
    expect(tabFromWorkspacePath("/gym/unknown", "/gym", GYM_TABS, "members")).toBe("members");
  });
});
