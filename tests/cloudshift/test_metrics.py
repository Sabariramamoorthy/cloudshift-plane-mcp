from datetime import date, datetime, timezone

from cloudshift.config import CloudShiftConfig
from cloudshift.services.metrics_service import annotate_issues, compute_metrics
from tests.cloudshift.fixtures.ce_workspace import ISSUES, LABELS, MODULE_MAP, STATES


def test_metrics_counts():
    cfg = CloudShiftConfig(timezone="Asia/Kolkata", stale_task_days=5, due_soon_hours=48)
    annotated = annotate_issues(
        ISSUES,
        states=STATES,
        labels=LABELS,
        config=cfg,
        as_of=date(2026, 7, 23),
        now=datetime(2026, 7, 23, 12, 0, tzinfo=timezone.utc),
        module_map=MODULE_MAP,
        project_identifier="DEMO",
    )
    metrics = compute_metrics(annotated)
    assert metrics.total == 5
    assert metrics.completed == 1
    assert metrics.blocked >= 1
    assert metrics.overdue >= 1
    assert metrics.unassigned >= 1
    assert metrics.stale >= 1
    assert metrics.completion_percentage == 20.0
