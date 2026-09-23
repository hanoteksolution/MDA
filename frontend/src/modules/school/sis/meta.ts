import { resources } from './config';

/** Page copy for School student-administration resources (headers, create buttons, empty states). */
const META: Record<string, [singular: string, description: string]> = {
 applications: ['Application', 'Track admission applications from submission through review, decision and enrollment.'],
 applicants: ['Applicant', 'Prospective students and their contact details before enrollment.'],
 students: ['Student', 'Manage enrolled students, placements, guardians and lifecycle changes.'],
 families: ['Family', 'Group siblings and guardians into households for communication and billing.'],
 guardians: ['Guardian', 'Parents and guardians linked to students and applicants.'],
 assessments: ['Assessment', 'Entrance assessments scheduled for admission applications.'],
 interviews: ['Interview', 'Admission interviews and their recommendations.'],
 decisions: ['Decision', 'Recorded admission decisions. Decisions are immutable.'],
 enrollments: ['Enrollment', 'Class and section placements per academic year.'],
 transitions: ['History entry', 'Transfers, withdrawals, suspensions and re-enrollments. Entries are immutable.'],
 'document-types': ['Document requirement', 'Documents required for admission and student records.'],
 'admission-policies': ['Admission policy', 'Campus rules for guardians, families, capacity and numbering.'],
 'relationship-types': ['Relationship type', 'Guardian relationship vocabulary (mother, uncle, sponsor…).'],
 'student-guardians': ['Student guardian link', 'Guardian relationships for enrolled students.'],
 'applicant-guardians': ['Applicant guardian link', 'Guardian relationships for applicants.'],
 'student-documents': ['Student document', 'Uploaded student documents and their verification status.'],
 'applicant-documents': ['Application document', 'Documents submitted with admission applications.'],
 'emergency-contacts': ['Emergency contact', 'Prioritised emergency contacts per student.'],
 notes: ['Student note', 'Private notes recorded against student records.'],
 employees: ['Employee', 'School employees available for teaching and administrative roles.'],
 'staff-profiles': ['Teaching staff profile', 'Teaching staff, specializations and weekly teaching capacity.'],
 'teacher-assignments': ['Teacher assignment', 'Class teacher and subject teacher assignments per academic year.'],
 classrooms: ['Room', 'Classrooms, labs and halls available for timetabling.'],
 periods: ['Period', 'Daily period structure used by timetables and period attendance.'],
 'timetable-versions': ['Timetable', 'Draft, published and archived timetable versions per campus and year.'],
 'timetable-entries': ['Lesson', 'Scheduled lessons inside a timetable version.'],
 'attendance-sessions': ['Attendance session', 'Daily and period attendance registers. Submitted sessions are locked.'],
 'attendance-records': ['Attendance record', 'Individual student attendance marks.'],
 'attendance-corrections': ['Attendance correction', 'Requested changes to submitted attendance, pending approval.'],
 'grade-schemes': ['Grade scheme', 'Grading scales used to convert percentages into grades.'],
 'grade-bands': ['Grade band', 'Score ranges within a grade scheme.'],
 assignments: ['Assignment', 'Homework and coursework assigned to subject offerings.'],
 submissions: ['Submission', 'Student submissions awaiting or completed grading.'],
 exams: ['Exam', 'Exams, moderated marks and published results.'],
 'academic-assessments': ['Academic assessment', 'Weighted assessment components within exams.'],
 'exam-schedules': ['Exam schedule', 'Rooms, invigilators and times for assessments.'],
 marks: ['Mark', 'Recorded marks per assessment and student.'],
 'result-publications': ['Result publication', 'Immutable published result versions.'],
 'report-cards': ['Report card', 'Published, versioned report cards per student.'],
 'promotion-batches': ['Promotion batch', 'Saved promotion previews and committed promotions.'],
 'promotion-items': ['Promotion outcome', 'Per-student promotion, repeat and graduation outcomes.'],
 'fee-settings': ['Finance mapping', 'Ledger account mappings for School receivables, advances and credits.'],
 'fee-categories': ['Fee category', 'Fee types with revenue mapping and recognition rules.'],
 'fee-structures': ['Fee structure', 'Fee schedules per academic year and class.'],
 'fee-lines': ['Fee line', 'Individual charges within a fee structure.'],
 'fee-discounts': ['Discount', 'Scholarships and discounts requiring approval.'],
 'fee-batches': ['Fee batch', 'Fee generation previews and issued batches.'],
 'fee-assignments': ['Assigned fee', 'Fees assigned to students by issued batches.'],
 'fee-invoices': ['School invoice link', 'Links between School fee batches and shared ERP invoices.'],
 'billing-invoices': ['Fee invoice', 'Issued fee invoices with payments and balances.'],
 'billing-methods': ['Payment method', 'Accepted payment methods and their ledger mappings.'],
 'billing-customers': ['Billing customer', 'Customers (payers) billed for student fees.'],
 'billing-receipts': ['Receipt', 'Collected payments and unallocated advances.'],
 'billing-allocations': ['Allocation', 'Receipt amounts allocated to fee invoices.'],
 'billing-credits': ['Credit note', 'Approved credits against issued fee lines.'],
 'billing-refunds': ['Refund', 'Refunds of unallocated funds.'],
 'billing-lines': ['Issued fee line', 'Individual lines on issued fee invoices.'],
 'billing-cost-centers': ['Cost center', 'Cost centers available for School finance reporting.'],
 'billing-business-units': ['Business unit', 'Business units available for School finance reporting.'],
};

export const singular = (resource: string) => META[resource]?.[0] ?? resources[resource]?.title ?? 'Record';
export const description = (resource: string) => META[resource]?.[1] ?? '';
/** Records that are written by workflows only (no generic edit/archive). */
export const immutable = (resource: string) => Boolean(resources[resource]?.readonly) || ['enrollments', 'assessments', 'interviews', 'attendance-sessions', 'attendance-records', 'attendance-corrections'].includes(resource);
export const editable = (resource: string) => !resources[resource]?.readonly && !['assessments', 'interviews'].includes(resource);
export const exportable = (resource: string) => ['students', 'applicants', 'guardians', 'families', 'enrollments'].includes(resource);
/** Class filter support: students via current enrollment, others via their own school_class_id. */
export const classFilter = (resource: string) => ['students', 'enrollments', 'applications'].includes(resource);

/** Read-only lists whose records are created by a dedicated workflow page. */
export const WORKFLOW_ENTRY: Record<string, { label: string; to: string; codes: string[] }> = {
 'attendance-sessions': { label: 'Take attendance', to: '/school/attendance', codes: ['school.attendance.take', 'school.attendance.take_any'] },
 'attendance-records': { label: 'Take attendance', to: '/school/attendance', codes: ['school.attendance.take', 'school.attendance.take_any'] },
 marks: { label: 'Enter marks', to: '/school/marks', codes: ['school.mark.enter'] },
 'promotion-batches': { label: 'New promotion', to: '/school/promotions', codes: ['school.promotion.preview'] },
 'promotion-items': { label: 'New promotion', to: '/school/promotions', codes: ['school.promotion.preview'] },
 'fee-batches': { label: 'Generate fees', to: '/school/finance/generate', codes: ['school.fee_batch.preview'] },
 'fee-assignments': { label: 'Generate fees', to: '/school/finance/generate', codes: ['school.fee_batch.preview'] },
 'billing-invoices': { label: 'Generate fees', to: '/school/finance/generate', codes: ['school.fee_batch.preview'] },
 'billing-receipts': { label: 'Record payment', to: '/school/finance/transactions', codes: ['school.billing_receipt.collect'] },
 'billing-allocations': { label: 'Allocate receipt', to: '/school/finance/transactions', codes: ['school.billing_allocation.allocate'] },
 'billing-credits': { label: 'Issue credit', to: '/school/finance/transactions', codes: ['school.billing_credit.issue'] },
 'billing-refunds': { label: 'Issue refund', to: '/school/finance/transactions', codes: ['school.billing_refund.issue'] },
 'result-publications': { label: 'Open exams', to: '/school/sis/exams', codes: ['school.exam.view'] },
 'report-cards': { label: 'Open exams', to: '/school/sis/exams', codes: ['school.exam.view'] },
};
