# Navigation Architecture — Module Switcher

**Date:** 2026-08-07  
**Status:** Implemented (PHASE 07)

---

## Behavior

- Header **Module Switcher** lists workspaces unlocked by `enabled_modules`.
- Selecting a workspace sets `uiStore.activeWorkspace` (persisted) and navigates to the workspace route.
- Sidebar soft-filters Operational/Catalog/Venue/Finance items by active workspace; Overview/Platform/System stay available.
- Path sync: `/gym`, `/pos`, `/pharmacy`, … update the active workspace.

Registry: `frontend/src/navigation/moduleWorkspaces.ts`

---

## Classification

| Piece | Action |
|-------|--------|
| Hardcoded sidebar sections | **KEEP** + workspace tags |
| Module switcher | **CREATE** ✓ |
| Per-module route from API metadata | later (Module.route already seeded) |
