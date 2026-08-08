"""Module dependency validation (PHASE 05)."""

from __future__ import annotations

from typing import Iterable

from apps.platform.models import Module


class ModuleDependencyError(ValueError):
    def __init__(self, message: str, *, missing: dict[str, list[str]] | None = None):
        super().__init__(message)
        self.code = "MODULE_DEPENDENCY"
        self.missing = missing or {}


class ModuleDependencyService:
    @staticmethod
    def expand_with_dependencies(codes: Iterable[str]) -> set[str]:
        """Return codes plus transitive required dependencies from catalog."""
        wanted = {str(c).strip().lower() for c in codes if c}
        by_code = {
            m.code: m
            for m in Module.active_objects().filter(is_active=True)
        }
        changed = True
        while changed:
            changed = False
            for code in list(wanted):
                module = by_code.get(code)
                if module is None:
                    continue
                for dep in module.required_dependency_codes():
                    if dep not in wanted:
                        wanted.add(dep)
                        changed = True
        return wanted

    @staticmethod
    def validate_enable_set(codes: Iterable[str]) -> set[str]:
        """
        Validate a proposed enabled set.

        Missing required deps are auto-added (returned set is expanded).
        Unknown codes raise ModuleDependencyError.
        """
        requested = {str(c).strip().lower() for c in codes if c}
        by_code = {
            m.code: m
            for m in Module.active_objects().filter(is_active=True)
        }
        unknown = sorted(requested - set(by_code.keys()))
        if unknown:
            raise ModuleDependencyError(
                f"Unknown module code(s): {', '.join(unknown)}.",
                missing={"unknown": unknown},
            )
        expanded = ModuleDependencyService.expand_with_dependencies(requested)
        return expanded

    @staticmethod
    def validate_disable(*, enabled_after: set[str]) -> None:
        """Reject disabling a module still required by another enabled module."""
        by_code = {
            m.code: m
            for m in Module.active_objects().filter(is_active=True, code__in=enabled_after)
        }
        missing: dict[str, list[str]] = {}
        for code, module in by_code.items():
            for dep in module.required_dependency_codes():
                if dep not in enabled_after:
                    missing.setdefault(code, []).append(dep)
        if missing:
            parts = [f"{k} requires {', '.join(v)}" for k, v in sorted(missing.items())]
            raise ModuleDependencyError(
                "Cannot disable modules still required by others: " + "; ".join(parts),
                missing=missing,
            )
