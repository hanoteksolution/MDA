"""Phase 6 verification: durable reports and the recorded School business date."""
import json
from datetime import date
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent

@pytest.fixture(autouse=True)
def school_baseline_date(request, monkeypatch):
    if request.node.path.name.startswith("test_school"):
        from django.utils import timezone
        original = timezone.localdate
        def business_date(value=None, timezone=None):
            return date(2026, 9, 21) if value is None else original(value, timezone)
        monkeypatch.setattr(timezone, "localdate", business_date)

def pytest_runtest_logreport(report):
    data = {"nodeid": report.nodeid, "when": report.when, "outcome": report.outcome}
    with (ROOT / "phase6-regression-events.jsonl").open("a") as handle:
        handle.write(json.dumps(data) + "\n")
    if report.failed:
        with (ROOT / "phase6-regression-diagnostics.txt").open("a") as handle:
            handle.write(f"\n{report.when.upper()} {report.nodeid}\n{report.longrepr}\n")

def pytest_sessionfinish(session, exitstatus):
    (ROOT / "phase6-regression-exit.json").write_text(json.dumps({"exit_code": int(exitstatus), "collected": session.testscollected}) + "\n")
