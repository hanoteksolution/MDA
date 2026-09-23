import {
  LayoutDashboard,
  ClipboardList,
  Users,
  BookOpen,
  Presentation,
  ClipboardCheck,
  Wallet,
  Settings,
  type LucideIcon,
} from "lucide-react";
import type { WorkspaceNavItem, WorkspaceNavSection } from "./businessWorkspaces";

/**
 * School workspace navigation. Every entry maps to an existing route and
 * backend resource; permissions mirror the codes the School API enforces
 * (`school.<resource>.<action>`), so a user never sees a link that 403s.
 */
type Entry = { to: string; label: string; permission: string[]; end?: boolean };
type Group = { label: string; icon: LucideIcon; entries: Entry[] };

const sis = (resource: string) => `/school/sis/${resource}`;
const academics = (resource: string) => `/school/academics/${resource}`;
const view = (...resources: string[]) => resources.map((r) => `school.${r}.view`);

export const SCHOOL_NAV_GROUPS: Group[] = [
  {
    label: "Admissions",
    icon: ClipboardList,
    entries: [
      { to: "/school/admissions", label: "Admissions overview", permission: view("admission"), end: true },
      { to: sis("applications"), label: "Applications", permission: view("admission") },
      { to: sis("applicants"), label: "Applicants", permission: view("applicant") },
      { to: sis("enrollments"), label: "Enrollment", permission: view("enrollment") },
    ],
  },
  {
    label: "Students",
    icon: Users,
    entries: [
      { to: sis("students"), label: "Students", permission: view("student") },
      { to: sis("guardians"), label: "Guardians", permission: view("guardian") },
      { to: sis("families"), label: "Families", permission: view("family") },
      { to: sis("transitions"), label: "Transfers & history", permission: view("student_transition") },
    ],
  },
  {
    label: "Academics",
    icon: BookOpen,
    entries: [
      { to: academics("academic-years"), label: "Academic years", permission: [...view("academic_year"), "school.academic.view"] },
      { to: academics("terms"), label: "Terms", permission: [...view("term"), "school.academic.view"] },
      { to: academics("campuses"), label: "Campuses", permission: view("campus") },
      { to: academics("classes"), label: "Classes", permission: view("class") },
      { to: academics("sections"), label: "Sections", permission: view("section") },
      { to: academics("subjects"), label: "Subjects", permission: view("subject") },
      { to: academics("subject-offerings"), label: "Subject offerings", permission: view("subject_offering") },
    ],
  },
  {
    label: "Teaching",
    icon: Presentation,
    entries: [
      { to: sis("staff-profiles"), label: "Teaching staff", permission: view("staff_profile") },
      { to: sis("teacher-assignments"), label: "Teacher assignments", permission: view("teacher_assignment") },
      { to: sis("employees"), label: "Employees", permission: view("employee") },
      { to: "/school/timetable", label: "Timetable", permission: view("timetable"), end: true },
      { to: sis("timetable-versions"), label: "Timetable versions", permission: view("timetable") },
      {
        to: "/school/attendance",
        label: "Take attendance",
        permission: ["school.attendance.take", "school.attendance.take_any", "school.attendance.view"],
        end: true,
      },
      { to: sis("attendance-sessions"), label: "Attendance history", permission: view("attendance") },
      { to: sis("attendance-corrections"), label: "Attendance corrections", permission: view("attendance_correction") },
    ],
  },
  {
    label: "Assessments",
    icon: ClipboardCheck,
    entries: [
      { to: sis("assignments"), label: "Assignments", permission: view("assignment") },
      { to: sis("submissions"), label: "Submissions & grading", permission: view("submission") },
      { to: sis("exams"), label: "Exams & results", permission: view("exam") },
      { to: "/school/marks", label: "Marks entry", permission: view("mark"), end: true },
      { to: sis("grade-schemes"), label: "Grading scales", permission: view("grade_scheme") },
      { to: sis("report-cards"), label: "Report cards", permission: view("report_card") },
      { to: "/school/promotions", label: "Promotions", permission: ["school.promotion.preview"], end: true },
      { to: sis("promotion-batches"), label: "Promotion history", permission: view("promotion") },
    ],
  },
  {
    label: "Finance",
    icon: Wallet,
    entries: [
      { to: "/school/finance/fees", label: "Student billing", permission: view("fee_finance"), end: true },
      { to: sis("fee-structures"), label: "Fee structures", permission: view("fee_structure") },
      { to: sis("fee-discounts"), label: "Scholarships & discounts", permission: view("fee_discount") },
      { to: "/school/finance/generate", label: "Generate fees", permission: ["school.fee_batch.preview"], end: true },
      { to: sis("billing-invoices"), label: "Fee invoices", permission: view("fee_invoice") },
      {
        to: "/school/finance/transactions",
        label: "Record payment",
        permission: [
          "school.billing_receipt.collect",
          "school.billing_allocation.allocate",
          "school.billing_credit.issue",
          "school.billing_refund.issue",
        ],
        end: true,
      },
      { to: sis("billing-receipts"), label: "Receipts & advances", permission: view("billing_receipt") },
      { to: sis("billing-customers"), label: "Billing customers", permission: view("billing_customer") },
    ],
  },
  {
    label: "School settings",
    icon: Settings,
    entries: [
      { to: "/school/settings", label: "School profile", permission: ["school.profile.view", "school.settings.view"], end: true },
      { to: academics("levels"), label: "Education levels", permission: view("level") },
      { to: academics("subject-categories"), label: "Subject categories", permission: view("subject_category") },
      { to: academics("shifts"), label: "Shifts", permission: view("shift") },
      { to: sis("periods"), label: "Timetable periods", permission: view("period") },
      { to: sis("classrooms"), label: "Rooms", permission: view("classroom") },
      { to: academics("campus-access"), label: "Campus access", permission: view("campus_access") },
      { to: sis("document-types"), label: "Document requirements", permission: view("document_type") },
      { to: sis("admission-policies"), label: "Admission policies", permission: view("admission_policy") },
      { to: sis("relationship-types"), label: "Relationship types", permission: view("relationship_type") },
      { to: sis("fee-categories"), label: "Fee categories", permission: view("fee_category") },
      { to: sis("fee-settings"), label: "Finance mappings", permission: view("fee_settings") },
      { to: sis("billing-methods"), label: "Payment methods", permission: view("billing_method") },
    ],
  },
];

/** Grouped, permission-filtered School sidebar. Empty groups are omitted. */
export function schoolNavSections(can: (codes: string[]) => boolean): WorkspaceNavSection[] {
  const sections: WorkspaceNavSection[] = [
    { label: "School", items: [{ to: "/school", label: "Dashboard", icon: LayoutDashboard, end: true, permission: "school.view" }] },
  ];
  for (const group of SCHOOL_NAV_GROUPS) {
    const items: WorkspaceNavItem[] = group.entries
      .filter((entry) => can(entry.permission))
      .map((entry) => ({ to: entry.to, label: entry.label, icon: group.icon, permission: entry.permission, module: "school", end: entry.end }));
    if (items.length) sections.push({ label: group.label, icon: group.icon, collapsible: true, items });
  }
  return sections;
}

/** The navigation group and entry that own a School path (used for breadcrumbs). */
export function schoolNavLocation(pathname: string): { group: string; label: string } | null {
  let best: { group: string; label: string; length: number } | null = null;
  for (const group of SCHOOL_NAV_GROUPS) {
    for (const entry of group.entries) {
      const hit = entry.end ? pathname === entry.to : pathname === entry.to || pathname.startsWith(`${entry.to}/`);
      if (hit && (!best || entry.to.length > best.length)) best = { group: group.label, label: entry.label, length: entry.to.length };
    }
  }
  return best && { group: best.group, label: best.label };
}

/**
 * Breadcrumb trail for a School page: School › Group › Entry › extra. Pages not
 * in the sidebar (child records such as interviews) use `fallback` instead.
 */
export function schoolBreadcrumbs(pathname: string, fallback: string, ...extra: string[]): string[] {
  const place = schoolNavLocation(pathname);
  const trail = ["School", ...(place ? [place.group, place.label] : [fallback]), ...extra].filter(Boolean);
  return trail.filter((crumb, i) => !trail.slice(0, i).includes(crumb));
}
