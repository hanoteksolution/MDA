# Industry-centric workspace architecture

Safari ERP top-level UX is **business verticals** (Restaurant, Gym, Pharmacy, Hotel, Property, Retail, Futsal). Shared POS / Sales / Inventory / Purchasing / Finance engines stay singleton underneath.

| Doc | Topic |
|---|---|
| [WORKSPACE_ARCHITECTURE.md](./WORKSPACE_ARCHITECTURE.md) | Target shape and principles |
| [SHARED_CAPABILITY_ARCHITECTURE.md](./SHARED_CAPABILITY_ARCHITECTURE.md) | One engine, many profiles |
| [WORKSPACE_REGISTRY.md](./WORKSPACE_REGISTRY.md) | Catalog codes |
| [TENANT_WORKSPACE_ARCHITECTURE.md](./TENANT_WORKSPACE_ARCHITECTURE.md) | Tenant enablement |
| [WORKSPACE_NAVIGATION.md](./WORKSPACE_NAVIGATION.md) | Switcher, sidebar, URLs |
| [WORKSPACE_DASHBOARD.md](./WORKSPACE_DASHBOARD.md) | Hub + workspace dashboards |
| [ACCOUNTING_INTEGRATION.md](./ACCOUNTING_INTEGRATION.md) | One CAE + BusinessUnit |
| [MIGRATION_PLAN.md](./MIGRATION_PLAN.md) | KEEP / EXTEND / REFACTOR / increment plan |

Increment 1 (shipped in FE): registry, hub cards, switcher, sidebar, `/restaurant/pos`-style aliases. Engines are not rewritten.
