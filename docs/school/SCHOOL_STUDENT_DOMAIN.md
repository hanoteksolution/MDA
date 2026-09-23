# School Phase 3 domain decisions

Completed Phase 3 scope and verification are recorded in [the Phase 3 report](SCHOOL_PHASE_3_IMPLEMENTATION.md), 2026-09-21. Phase 2 stays authoritative for campus, academic catalog and authorization.

| Existing area | Classification | Phase 3 decision |
|---|---|---|
| Tenant/Company/Branch/User/RBAC | KEEP | Reuse identities, campus access and effective permissions |
| SchoolAccess / academic catalogs | EXTEND | Student ownership, relationship visibility and history dependency checks |
| Audit engine | KEEP | Append workflow events; redact sensitive note/document content |
| Customer | KEEP | Sales/customer balance identity is not a suitable child/guardian master; no forced billing account |
| Student/admissions/guardian/person abstraction | CREATE | None exists; separate prospective identity, application, long-lived student and enrollment |
| Property/Travel documents | KEEP | Vertical-specific URL records, not a secure shared document service |
| School private files | CREATE | Opaque private storage, authenticated scoped downloads, validated bounded uploads |
| Sales numbering | KEEP | Invoice-only kinds/seeding do not fit student identities; School sequences use the proven tenant transaction lock |
| CSV/Excel import | No reusable transactional import pipeline found | Student import is conditional in this phase; do not add an unreviewed bulk import shortcut |
| Shared export | EXTEND | Scoped, permission-checked streaming CSV with formula-safe cells |

Enrollment is placement history. Student.branch is the current primary campus used to authorize the identity; it is not the source of class/year/section truth. Historical enrollment is independently campus-scoped and immutable after transition. A transfer must be authorized at source and destination and advances Student.branch atomically. Old-campus users retain authorized historical placement data, not the new campus's Student 360.

Family and Guardian are reusable tenant identities, visible from their home campus or an authorized linked student/applicant. They are not automatically system users. Linking an existing contact requires object visibility, same tenant and permission; sibling relationships never duplicate the guardian automatically.

Defaults: one active enrollment per student across campuses/years, term-independent current scope, optional roll number unique per year/campus/class/section, inclusive enrollment dates and transfer closure the preceding day. Current placement requires active enrollment, active academic year and today's date inside placement bounds. Only immediate/past effective transfers are executable; future scheduling is outside scope. Capacity blocks by default; explicit policy can warn or allow authorized reasoned override. Number prefixes support literal text plus {year}/{campus}; tenant identity numbers remain unique regardless of sequence scope.

Admission decisions and student lifecycle are command-only. Documents must satisfy configured requirements at acceptance and conversion, or an explicit audited override with reason. Confidential note content is absent from general audit snapshots and requires its own read/write permission. Sensitive files are never served by public media URLs.
