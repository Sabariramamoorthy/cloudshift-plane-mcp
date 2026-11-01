"""Synthetic CE-shaped fixtures for CloudShift Wave 2 tests."""

from __future__ import annotations

PROJECT = {
    "id": "proj-1",
    "name": "Demo Project",
    "identifier": "DEMO",
    "archived_at": None,
}

STATES = [
    {"id": "s-backlog", "name": "Backlog", "group": "backlog"},
    {"id": "s-todo", "name": "Todo", "group": "unstarted"},
    {"id": "s-progress", "name": "In Progress", "group": "started"},
    {"id": "s-done", "name": "Done", "group": "completed"},
    {"id": "s-cancel", "name": "Cancelled", "group": "cancelled"},
    {"id": "s-blocked", "name": "Blocked", "group": "started"},
]

LABELS = [
    {"id": "l-blocked", "name": "blocked"},
    {"id": "l-bug", "name": "bug"},
]

MEMBERS = [
    {
        "id": "u-alex",
        "first_name": "Alex",
        "last_name": "S",
        "email": "alex@example.com",
        "display_name": "alex",
    },
    {
        "id": "u-alex2",
        "first_name": "Alex",
        "last_name": "Rivera",
        "email": "alex.k@example.com",
        "display_name": "alexk",
    },
    {
        "id": "u-sam",
        "first_name": "Sam",
        "last_name": "M",
        "email": "sam@example.com",
        "display_name": "sam",
    },
]

MODULES = [
    {"id": "m-att", "name": "Attendance"},
    {"id": "m-pay", "name": "Payroll"},
]

CYCLES = [
    {
        "id": "c-11",
        "name": "Sprint 11",
        "start_date": "2026-07-01",
        "end_date": "2026-07-14",
        "archived_at": None,
    }
]

ISSUES = [
    {
        "id": "i1",
        "name": "Attendance Correction",
        "sequence_id": 123,
        "priority": "high",
        "state": "s-progress",
        "assignees": ["u-alex"],
        "labels": [],
        "target_date": "2026-07-10",
        "updated_at": "2026-07-20T10:00:00+00:00",
        "completed_at": None,
        "is_draft": False,
        "project_identifier": "DEMO",
    },
    {
        "id": "i2",
        "name": "Payroll Calculation API",
        "sequence_id": 108,
        "priority": "urgent",
        "state": "s-todo",
        "assignees": ["u-alex"],
        "labels": [],
        "target_date": "2026-07-25",
        "updated_at": "2026-07-22T10:00:00+00:00",
        "completed_at": None,
        "is_draft": False,
        "project_identifier": "DEMO",
    },
    {
        "id": "i3",
        "name": "Salary Revision",
        "sequence_id": 115,
        "priority": "high",
        "state": "s-blocked",
        "assignees": ["u-alex"],
        "labels": ["l-blocked"],
        "target_date": "2026-07-01",
        "updated_at": "2026-07-01T10:00:00+00:00",
        "completed_at": None,
        "is_draft": False,
        "project_identifier": "DEMO",
    },
    {
        "id": "i4",
        "name": "Done Payroll UI",
        "sequence_id": 90,
        "priority": "medium",
        "state": "s-done",
        "assignees": ["u-sam"],
        "labels": [],
        "target_date": "2026-07-05",
        "updated_at": "2026-07-23T08:00:00+00:00",
        "completed_at": "2026-07-23T08:00:00+00:00",
        "is_draft": False,
        "project_identifier": "DEMO",
    },
    {
        "id": "i5",
        "name": "Unassigned Backlog",
        "sequence_id": 1,
        "priority": "none",
        "state": "s-backlog",
        "assignees": [],
        "labels": [],
        "target_date": None,
        "updated_at": "2026-06-01T10:00:00+00:00",
        "completed_at": None,
        "is_draft": False,
        "project_identifier": "DEMO",
    },
]

MODULE_MAP = {
    "i1": {"m-att"},
    "i2": {"m-pay"},
    "i3": {"m-pay"},
    "i4": {"m-pay"},
}

CYCLE_MAP = {
    "i1": {"c-11"},
    "i2": {"c-11"},
    "i3": {"c-11"},
}
