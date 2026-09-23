import { describe, expect, it } from "vitest";
import { SCHOOL_NAV_GROUPS, schoolBreadcrumbs, schoolNavLocation, schoolNavSections } from "./schoolNavigation";
import { industryNavSections } from "./businessWorkspaces";
import { resources as sisResources } from "@/modules/school/sis/config";
import { resources as foundationResources } from "@/modules/school/foundation";

const entries = SCHOOL_NAV_GROUPS.flatMap((g) => g.entries);
// Fixed School routes registered in app/workspaceRoutes.tsx.
const FIXED = new Set([
  "/school/admissions",
  "/school/attendance",
  "/school/timetable",
  "/school/marks",
  "/school/promotions",
  "/school/finance/fees",
  "/school/finance/generate",
  "/school/finance/transactions",
  "/school/settings",
]);

describe("School navigation map", () => {
  it("links only to routes and resources that exist", () => {
    for (const entry of entries) {
      const sis = entry.to.match(/^\/school\/sis\/([^/]+)$/);
      const academic = entry.to.match(/^\/school\/academics\/([^/]+)$/);
      if (sis) expect(sisResources[sis[1]], entry.to).toBeDefined();
      else if (academic) expect(foundationResources[academic[1]], entry.to).toBeDefined();
      else expect(FIXED.has(entry.to), entry.to).toBe(true);
    }
    expect(new Set(entries.map((e) => e.to)).size).toBe(entries.length);
  });

  it("requires the same view permission the School API enforces", () => {
    for (const entry of entries) {
      const sis = entry.to.match(/^\/school\/sis\/([^/]+)$/);
      if (sis) expect(entry.permission).toContain(`school.${sisResources[sis[1]].permission}.view`);
      const academic = entry.to.match(/^\/school\/academics\/([^/]+)$/);
      if (academic) expect(entry.permission).toContain(`school.${foundationResources[academic[1]].permission}.view`);
    }
  });

  it("groups the module into the target information architecture", () => {
    expect(SCHOOL_NAV_GROUPS.map((g) => g.label)).toEqual([
      "Admissions",
      "Students",
      "Academics",
      "Teaching",
      "Assessments",
      "Finance",
      "School settings",
    ]);
    const sections = schoolNavSections(() => true);
    expect(sections[0]).toMatchObject({ label: "School", items: [{ to: "/school", label: "Dashboard", end: true }] });
    expect(sections.slice(1).every((s) => s.collapsible && s.icon)).toBe(true);
  });

  it("hides entries and whole groups the user cannot access", () => {
    const granted = new Set(["school.student.view", "school.guardian.view"]);
    const sections = schoolNavSections((codes) => codes.some((c) => granted.has(c)));
    expect(sections.map((s) => s.label)).toEqual(["School", "Students"]);
    expect(sections[1].items.map((i) => i.label)).toEqual(["Students", "Guardians"]);
  });

  it("honours legacy academic aliases for calendars", () => {
    const sections = schoolNavSections((codes) => codes.includes("school.academic.view"));
    expect(sections.find((s) => s.label === "Academics")?.items.map((i) => i.label)).toEqual(["Academic years", "Terms"]);
  });
});

describe("School workspace sidebar integration", () => {
  it("uses grouped School navigation inside the shared sidebar builder", () => {
    const sections = industryNavSections("school", { hasPermission: (c) => c === "school.view" || c === "school.admission.view", enabled: ["school"] });
    expect(sections.map((s) => s.label)).toEqual(["School", "Admissions", "Platform"]);
    expect(sections[1].items.map((i) => i.to)).toEqual(["/school/admissions", "/school/sis/applications"]);
  });

  it("shows no School features when the module is disabled", () => {
    const sections = industryNavSections("school", { hasPermission: () => true, enabled: ["retail"] });
    expect(sections.map((s) => s.label)).toEqual(["School", "Platform"]);
  });

  it("gives elevated users every group", () => {
    const sections = industryNavSections("school", { elevated: true, enabled: [] });
    expect(sections).toHaveLength(SCHOOL_NAV_GROUPS.length + 2);
  });
});

describe("School breadcrumbs", () => {
  it("derive group and entry from the path, including detail pages", () => {
    expect(schoolNavLocation("/school/sis/students/abc")).toEqual({ group: "Students", label: "Students" });
    expect(schoolBreadcrumbs("/school/sis/students/abc", "Students", "Amina Yusuf")).toEqual(["School", "Students", "Amina Yusuf"]);
    expect(schoolBreadcrumbs("/school/attendance", "Attendance")).toEqual(["School", "Teaching", "Take attendance"]);
    expect(schoolBreadcrumbs("/school/academics/classes/1/edit", "Classes", "Edit")).toEqual(["School", "Academics", "Classes", "Edit"]);
  });

  it("do not confuse sibling resources that share a prefix", () => {
    expect(schoolNavLocation("/school/sis/student-guardians")).toBeNull();
    expect(schoolBreadcrumbs("/school/sis/interviews/9", "Interviews", "Details")).toEqual(["School", "Interviews", "Details"]);
  });
});
