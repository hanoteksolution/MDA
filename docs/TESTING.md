# MDA ERP — Testing Program (STEP 32)

Structured backend test layers for the shared-schema multi-tenant ERP.

## Layers

| Layer | Location | Marker | Purpose |
|-------|----------|--------|---------|
| Unit | `backend/tests/unit/` | `unit` (default) | Services, models, serializers, permissions |
| Integration | `backend/tests/integration/` | `integration` | HTTP API + service + DB end-to-end |
| Isolation | `unit/test_tenant_isolation.py`, `integration/test_tenant_isolation_api.py` | `isolation` | Cross-tenant scoping at service and API |
| Critical paths | `integration/test_critical_*.py` | `critical` | POS checkout, receive stock, gym check-in, pharmacy FEFO sale |

Frontend E2E (Playwright/Cypress) is deferred — API integration covers critical flows for now.

## Priority suites (must stay green)

1. **Tenant isolation** — list scoping, barcode lookup, cross-tenant write blocked
2. **POS checkout** — stock decrement, idempotency
3. **Receive stock** — PO receive increases inventory
4. **Gym check-in** — active membership check-in, duplicate blocked
5. **Pharmacy batch sale** — FEFO preview + POS sale deducts earliest batch first
6. **Health probes** — `test_health_step34.py` (database, cache, readiness)

## Commands

```bash
make test              # full backend suite
make test-unit         # unit tests only
make test-integration  # integration tests only
make test-critical     # critical business paths
make test-isolation    # tenant boundary tests
```

From `backend/`:

```bash
pytest                          # all
pytest -m critical              # critical paths only
pytest -m "integration and not critical"  # non-critical integration
pytest tests/unit/test_pos_step12.py -v   # single file
```

## Shared fixtures

- `tests/helpers/shop_factory.py` — `ShopFactory.create()` builds tenant, modules, admin/cashier user, product + stock
- `tests/integration/conftest.py` — `retail_shop`, `gym_shop`, `pharmacy_shop`, `two_shops`, `auth_client`
- `tests/conftest.py` — `api_client`, `user`, `authenticated_client`

## Adding tests

- **New business rule** → unit test on the service first
- **New API endpoint** → integration test if it is user-facing or security-sensitive
- **Tenant-scoped model** → add isolation case (service + API if exposed)
- Mark integration/critical/isolation tests with `@pytest.mark.*` for selective CI

## CI recommendation

```yaml
- run: make test-unit
- run: make test-critical
- run: make test-isolation
```

Full suite (`make test`) before release.
