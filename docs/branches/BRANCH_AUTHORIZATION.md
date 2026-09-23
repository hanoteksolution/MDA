# Branch Authorization

How the ERP decides **which branches an actor may touch** and **which of their
permissions apply in each one**. Written in Branch Phase 2; the contract below is what
every later phase (POS, transfers, finance, reports) builds on.

The single implementation is [`backend/core/branching.py`](../../backend/core/branching.py).
Modules must not re-implement branch filtering — there is one place to audit.

## 1. The model

```
Tenant / Company
   └── Branch                     settings_app.Branch (canonical, decision D1)
         ├── UserBranchAccess     who may act here, and from when to when
         │     └── BranchAccessProfile   which of their permissions apply here
         ├── Warehouse
         │     └── StockLocation
         ├── PosTerminal
         └── CashRegister
```

`UserBranchAccess` answers *where*; `BranchAccessProfile` answers *what*. They are
separate because the same profile ("Branch Staff") is reused across many branches,
and the same user routinely holds different profiles in different branches.

## 2. Two rules that must never be weakened

**A profile narrows; it never widens.** The effective permission set in a branch is

```
branch_permissions(user, branch) = global_permissions(user) ∩ profile_permissions(branch)
```

where `global_permissions` is the existing, unchanged `(role ∪ direct grants) − revokes`.
A profile that lists `finance.approve` gives it to nobody who did not already hold it
globally. Branch access is therefore **not a privilege-escalation path**, and an
administrator who can grant branch access cannot use it to manufacture rights.

A row with **no** profile means "no narrowing" — the user's full global permission set
applies in that branch. That is what keeps every existing single-branch user working
unchanged.

**The requested branch is untrusted input.** `X-Branch-Id` (header), `branch_id`
(query string) and any branch id in a request body are read, then *intersected* with
what the user actually holds. Changing the value can only ever shrink the result set.
There is no code path in which a supplied id widens scope.

## 3. Resolution order

`resolve_branch_scope(request, permission=..., allow_all=..., use_default=...)`:

1. Reject unauthenticated callers.
2. Resolve the tenant through the existing `core.tenancy.resolve_acting_tenant`. Branch
   scope is always computed *inside* an already-resolved tenant, never across tenants.
3. Compute the accessible branch set:
   * **elevated admin** (`super_admin` / `platform_admin` / superuser) → every branch in
     the acting tenant, matching how they already bypass tenant scope;
   * otherwise → the branches from that user's **effective** `UserBranchAccess` rows;
   * **legacy fallback** → if the user has *no* access rows at all, their historical
     `User.branch`. See §6.
4. If `permission` was given, drop every branch in which that codename is not effective
   (§2). This is how one user holds POS rights in one branch and read-only in another.
5. Apply the request's selection:
   * nothing sent → the whole accessible set, `is_all = True`;
   * `all` → the whole accessible set, `requested_all = True` (rejected outright when
     the endpoint passes `allow_all=False`);
   * a branch id → `403` if it is not in the accessible set, otherwise exactly that one
     branch, `explicit = True`.
6. Return a frozen `BranchScope`.

"Effective" for an access row means: not soft-deleted, `status = ACTIVE`, `starts_on`
has passed (or is empty), `ends_on` has not passed (or is empty), and the branch itself
is active and not soft-deleted. Suspended, ended, future-dated and expired grants all
resolve to **no access**.

## 4. Using a scope

| Call | Meaning |
|---|---|
| `scope.filter(qs, field_name="branch_id")` | Narrow a queryset. An empty scope filters to `none()`, never to everything. |
| `scope.allows(branch_id)` | Membership test for a single row. |
| `scope.require_single("a POS sale")` | The write path. Returns the one branch or refuses. |
| `apply_branch_scope(qs, request=..., permission=...)` | The convenience entry point modules use. |
| `HasBranchPermission("pos.access")` | DRF permission class; also attaches `request.branch_scope`. |

### Why `require_single` is not simply "reject `is_all`"

Writing to "all branches" is meaningless, so it must be refused — but the overwhelming
majority of existing tenants have exactly one branch and send no header at all. Refusing
those would break every current POS installation on upgrade. So the rule is
**ambiguity, not breadth**:

* the client explicitly asked for `all` → **refuse**;
* the scope contains more than one branch → **refuse**, ask the user to pick;
* the scope contains exactly one branch → proceed, it is unambiguous;
* the scope is empty → `403`.

POS, stock mutations, transfers and any other write therefore call `require_single()`
and never guess.

## 5. Failure modes are deliberate

| Situation | Result | Why |
|---|---|---|
| Branch id of another tenant | `403` | Identical response to an unknown id, so the API cannot be used to probe which tenants or branches exist. |
| Unknown / random UUID | `403` | Same as above. |
| Malformed id (`"'; DROP TABLE…"`) | `400` | A parse failure, not an authorisation answer. |
| No access rows and no `User.branch` | empty scope; writes `403` | Fail closed. |
| Branch deactivated while a user holds access | falls out of scope | Status is re-evaluated per request, not cached in the token. |

Nothing is silently ignored and nothing is silently widened.

## 6. Migration safety

The fallback in step 3 is what makes the backfill safe to run gradually: a user who has
not been backfilled yet keeps exactly today's behaviour through `User.branch`. The
moment that user gains **any** `UserBranchAccess` row, the rows become authoritative and
the legacy branch is no longer added — otherwise revoking access would be impossible for
anyone whose `User.branch` still pointed at the old branch.

`User.branch` stays nullable and is not removed in this project.

## 7. School

School keeps `SchoolCampusAccess` as its own source of truth. The backfill deliberately
does **not** copy campus access into `UserBranchAccess`, and does not read it when
resolving scope: copying it would silently grant retail branch rights to teachers, and
reading it would entangle two authorisation systems that are being kept separate on
purpose. A School-only tenant is unaffected by everything in this document.

## 8. Worked example

Ahmed, an `admin`-role user of one tenant:

| Branch | Access row | Profile | Effective |
|---|---|---|---|
| Hodan | yes, default | `POS_SALES` (pos, sales, inventory) | POS, sales, inventory |
| Bakaaro | yes | `VIEW_ONLY` (inventory.view) | inventory view only |
| Main | **none** | — | nothing at all |

* `GET /organization/my-branches/` returns Hodan and Bakaaro. Main is not listed.
* `X-Branch-Id: <Main>` → `403`, on every endpoint.
* `resolve_branch_scope(permission="pos.access")` → Hodan only.
* `resolve_branch_scope(permission="inventory.view")` → Hodan and Bakaaro.
* A POS sale with no header → refused as ambiguous (two branches); with
  `X-Branch-Id: <Hodan>` → allowed; with `X-Branch-Id: <Bakaaro>` → `403`.

Covered by `tests/unit/test_branch_rbac.py::test_worked_example_different_rights_per_branch`
and `tests/unit/test_branch_scope.py::test_permission_filter_narrows_scope_per_branch`.

## 9. Frontend

`frontend/src/store/branchStore.ts` holds only branches the API returned, and
`frontend/src/services/api/branchContext.ts` attaches `X-Branch-Id` to requests. The
store refuses to select a branch that is not in that list, and drops a remembered branch
that is no longer accessible.

This is a **usability guard, not the security boundary**. Every check above is re-run on
the server for every request; a tampered `localStorage` value or a hand-edited header
changes nothing.

## 10. Known limitations

1. Cross-tenant consistency (a `Warehouse` whose `Branch` belongs to another tenant) is
   enforced in model `clean()` and in the services, and reported by
   `branch_migration_report`. It is **not** a database constraint — Django cannot express
   a cross-table check — so a raw SQL writer could still create one. A trigger would be
   needed for full enforcement; recorded as technical debt.
2. `branch_permissions` issues one query per branch when a scope is filtered by
   permission. Fine at today's branch counts; revisit if a tenant runs dozens of branches.
3. Object-level checks on *existing* rows are done by scoping the queryset (`_get()` in
   the views), not by a DRF `has_object_permission`. Both are safe, but the pattern must
   be followed consistently by later phases.
