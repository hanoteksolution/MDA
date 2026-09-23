import { describe, expect, it } from "vitest";
import { overviewNavSections, platformNavSections } from "./businessWorkspaces";

const links = (sections: { items: { to: string }[] }[]) => sections.flatMap((s) => s.items.map((i) => i.to));

describe("Platform Admin → Integrations navigation", () => {
  it("is shown to elevated platform users", () => {
    expect(links(platformNavSections("platform", { elevated: true }))).toContain("/platform/integrations");
    expect(links(overviewNavSections([], { elevated: true, includePlatform: true }))).toContain("/platform/integrations");
  });

  it("is hidden from non-elevated users, even with platform.view or integrations permissions", () => {
    const has = (c: string) => ["platform.view", "integrations.view", "integrations.manage"].includes(c);
    expect(links(platformNavSections("platform", { hasPermission: has }))).not.toContain("/platform/integrations");
    expect(links(overviewNavSections([], { hasPermission: has, includePlatform: true }))).not.toContain("/platform/integrations");
  });
});
