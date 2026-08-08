# Module Dependencies

**Date:** 2026-08-07  
**Status:** Design — **CREATE** engine (not implemented)

---

## Principle

Backend is authoritative. FE may preview; enable/disable APIs must validate.

---

## Target rules

| Module | Requires | Optional |
|--------|----------|----------|
| `pharmacy` | `inventory`, `pos` | `purchases`, `finance` |
| `cafeteria` / `restaurant` | `pos` | `inventory`, `purchases`, `finance` |
| `gym` | — (finance via perms) | `pos`, `inventory` |
| `hotel` | — | `pos`, `restaurant`, `cafeteria`, `inventory` |
| `housing_rental` | `property_management` | `finance` |
| `office_rental` | `property_management` | `finance` |
| `supermarket` / `retail` | `pos`, `inventory` | `purchases` |

When enabling M, auto-enable required deps (or reject with structured error):

```json
{ "code": "MODULE_DEPENDENCY", "missing": ["inventory"] }
```

When disabling M, block if other enabled modules require it (unless cascade disable with confirm).

---

## Implementation sketch

```text
Module.dependencies: JSON list of codes   # EXTEND field
OR ModuleDependency(module, requires_module) table

ModuleDependencyService.validate_enable(tenant, codes) -> ok | errors
Called from: platform PUT tenant modules, onboarding, demo provision
```

---

## Classification

| Piece | Action |
|-------|--------|
| Ad-hoc FE assumptions | **DEPRECATE** |
| Middleware path map | **KEEP** |
| Dependency validator | **CREATE** |
