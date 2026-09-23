import { describe, expect, it } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { BookOpen, LayoutDashboard } from "lucide-react";
import { SidebarSection, sectionActive } from "./SidebarSection";
import type { WorkspaceNavSection } from "@/navigation/businessWorkspaces";

const group: WorkspaceNavSection = {
  label: "Academics",
  icon: BookOpen,
  collapsible: true,
  items: [
    { to: "/school/academics/academic-years", label: "Academic years", icon: BookOpen },
    { to: "/school/academics/classes", label: "Classes", icon: BookOpen },
  ],
};
const flat: WorkspaceNavSection = { label: "School", items: [{ to: "/school", label: "Dashboard", icon: LayoutDashboard, end: true }] };

const render = (section: WorkspaceNavSection, pathname: string, opts: { collapsed?: boolean; open?: boolean } = {}) =>
  renderToStaticMarkup(
    <MemoryRouter initialEntries={[pathname]}>
      <SidebarSection section={section} pathname={pathname} collapsed={Boolean(opts.collapsed)} open={Boolean(opts.open)} onToggle={() => undefined} />
    </MemoryRouter>
  );

describe("SidebarSection", () => {
  it("renders an accessible disclosure for expanded groups", () => {
    const html = render(group, "/school/academics/classes/1", { open: true });
    expect(html).toContain('aria-expanded="true"');
    expect(html).toContain('aria-controls="nav-group-academics"');
    expect(html).toContain('id="nav-group-academics" role="group" aria-label="Academics"');
    expect(html).toContain('href="/school/academics/classes"');
    expect(html).toMatch(/aria-current="page"[^>]*>|href="\/school\/academics\/classes"[^>]*aria-current="page"/);
  });

  it("hides items of a closed group", () => {
    const html = render(group, "/school", { open: false });
    expect(html).toContain('aria-expanded="false"');
    expect(html).not.toContain("/school/academics/classes");
  });

  it("collapses a group to one labelled icon in the narrow rail", () => {
    const html = render(group, "/school/academics/classes", { collapsed: true });
    expect(html.match(/<a /g)).toHaveLength(1);
    expect(html).toContain('aria-label="Academics"');
    expect(html).toContain('href="/school/academics/classes"');
    const idle = render(group, "/school", { collapsed: true });
    expect(idle).toContain('href="/school/academics/academic-years"');
  });

  it("keeps non-collapsible sections as labelled flat lists", () => {
    const html = render(flat, "/school");
    expect(html).toContain(">School</p>");
    expect(html).toContain('aria-label="Dashboard"');
    expect(html).not.toContain("aria-expanded");
  });

  it("detects the active group without matching sibling prefixes", () => {
    expect(sectionActive(group, "/school/academics/classes/9/edit")).toBe(true);
    expect(sectionActive(group, "/school/academics/classes-archive")).toBe(false);
    expect(sectionActive(flat, "/school/sis")).toBe(false);
  });
});
