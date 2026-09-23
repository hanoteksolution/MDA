# School Management — Reporting Matrix

**Date:** 2026-09-01  
**Engine:** School-specific reports overlay on `apps.reports` + `apps.finance` + school queryset services

---

## Report Categories

### Academic Reports

| Report | Data source | Filters | Export | Phase |
|---|---|---|---|---|
| Student Enrollment Summary | `StudentEnrollment` | year, branch, class, status | CSV, PDF | 16 |
| Admissions Pipeline | `Applicant` | date range, status, class | CSV, PDF | 16 |
| Class Lists | `Student` + enrollment | year, class, section | PDF (print roster) | 16 |
| Student Directory | `Student` | branch, class, status | CSV, Excel | 16 |
| Attendance Summary | `StudentAttendance` | date range, class, student | CSV, PDF | 16 |
| Daily Attendance Register | `StudentAttendance` | date, section | PDF | 16 |
| Teacher Attendance | staff attendance / HR | date range | CSV | 16 |
| Subject Performance | `MarkEntry` | exam, subject, class | CSV, PDF | 16 |
| Exam Performance | `Exam` + marks | exam, class | PDF | 16 |
| Class Performance | aggregated marks | term, class | PDF, chart | 16 |
| Student Performance | per student | student, year | PDF | 16 |
| Grade Distribution | marks + grade scale | exam, class | chart | 16 |
| Failing Students | marks < pass | exam, class | CSV, PDF | 16 |
| Top Students | rank by average | exam, class, limit | PDF | 16 |
| Promotion Summary | promotion batch | year | PDF | 16 |

### Fees Reports

| Report | Data source | Filters | Export | Phase |
|---|---|---|---|---|
| Fee Collection Summary | invoices + payments | date, term, class | CSV, PDF | 16 |
| Outstanding Fees | open invoices | class, overdue days | CSV, PDF | 16 |
| Overdue Fees | invoices past due | branch, amount | CSV + alerts | 16 |
| Student Balance Statement | student fee ledger | student | PDF | 16 |
| Discounts & Scholarships | `Scholarship` | date, type | CSV | 16 |
| Revenue by Fee Type | invoice lines | term, type | CSV, chart | 16 |
| Payment Methods | payments | date range | CSV | 16 |
| Daily Collection | payments | date | PDF (receipt book) | 16 |

### Finance Reports (Central Engine, School Filter)

| Report | Engine | School filter | Phase |
|---|---|---|---|
| Income Statement | `finance` P&L | cost_center = school branch | 16 |
| Expense Report | `finance` | cost_center | 16 |
| Accounts Receivable Aging | `finance` | school invoice tag | 16 |
| Cash & Bank Summary | `finance` | branch | 16 |
| Budget vs Actual | `finance` (if budget enabled) | school cost center | 19 |
| Balance Sheet | `finance` | branch/tenant | 16 |
| Cash Flow | `finance` | branch | 16 |
| Payroll Cost | finance / future hrm | school staff | 19 |

### Transport Reports

| Report | Filters | Export | Phase |
|---|---|---|---|
| Routes Summary | status | CSV | 16 |
| Students per Route | route | PDF roster | 16 |
| Transport Fee Collection | transport fee type | CSV | 16 |
| Vehicle Utilization | vehicle | CSV | 16 |

### Library Reports

| Report | Filters | Export | Phase |
|---|---|---|---|
| Borrowing Activity | date range | CSV | 16 |
| Overdue Books | days overdue | CSV, notify | 16 |
| Lost / Damaged Books | status | CSV | 16 |
| Fine Collection | date range | CSV | 16 |
| Catalog Summary | category | CSV | 16 |

### Inventory Reports (Shared Engine)

| Report | School context | Phase |
|---|---|---|
| Stock on Hand | uniform/supply categories | 16 |
| Low Stock Alert | school warehouse | 16 |
| Asset Assignment | IT/furniture tagged school | 16 |
| Issue/Return Log | school inventory | 16 |

### HR / Staff Reports

| Report | Source | Phase |
|---|---|---|
| Staff Directory | `SchoolStaffProfile` | 16 |
| Teacher Workload | assignments + timetable hours | 16 |
| Staff Performance | `StaffEvaluation` (existing) | 16 |

---

## Dashboard Widgets (`/school` home)

| Widget | KPI / Chart | Data |
|---|---|---|
| Total Students | number | active students |
| Active Students | number | status=active |
| New Admissions | number | this month applicants enrolled |
| Attendance Today | % | present / total today |
| Teachers | number | active staff type=teacher |
| Classes | number | grade levels × sections |
| Outstanding Fees | currency | sum open invoices |
| Fees Collected | currency | payments this month |
| Today's Payments | currency | payments today |
| Upcoming Exams | list | next 7 days schedules |
| Upcoming Events | list | calendar |
| Library Overdue | number | overdue borrowings |
| Transport Active | number | route assignments |
| Payroll Due | currency | next payroll period (future) |
| Enrollment Trend | line chart | 12 months |
| Attendance Trend | line chart | 30 days |
| Fee Collection | bar chart | by month |
| Academic Performance | bar chart | class averages |
| Gender Distribution | pie chart | optional, configurable |
| Class Distribution | bar chart | students per class |
| Recent Payments | table | last 10 |
| Recent Admissions | table | last 10 |
| Alerts | list | overdue fees, absences, etc. |

---

## Report API Endpoints

See `SCHOOL_API_MATRIX.md` → Reports section.

All reports support:
- `?format=csv|pdf|json`
- `?branch_id=`
- `?academic_year_id=`
- `?date_from=&date_to=`

---

## Report Card (Special Document)

Not a tabular report — generated PDF per student:

- Template engine: configurable HTML → PDF (reuse sales receipt PDF pattern)
- Data: marks, grades, attendance %, comments, conduct
- Verification: optional QR code with serial number
- Storage: document engine + `ReportCard.pdf_url`

---

## Permissions

All reports require `school.reports.view` minimum.  
Financial reports additionally require `school.fees.view` or shared `finance.view`.  
Discipline reports require `school.discipline.view`.

Parent/student portals: subset of reports scoped to own children/self only.

---

## Related Documents

- `SCHOOL_API_MATRIX.md`
- `SCHOOL_COMPLETION_MATRIX.md`
- `docs/accounting/FINANCIAL_REPORTING.md`
