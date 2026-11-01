import pytest

from cloudshift.errors import CloudShiftError, CloudShiftErrorCode
from cloudshift.utils.resolvers import resolve_member, resolve_project, resolve_work_item
from tests.cloudshift.fixtures.ce_workspace import ISSUES, MEMBERS, PROJECT


def test_resolve_project_by_identifier():
    hit = resolve_project("DEMO", [PROJECT])
    assert hit.id == "proj-1"


def test_resolve_project_by_name():
    hit = resolve_project("Demo Project", [PROJECT])
    assert hit.id == "proj-1"


def test_member_ambiguity():
    with pytest.raises(CloudShiftError) as exc:
        resolve_member("Alex", MEMBERS)
    assert exc.value.code == CloudShiftErrorCode.MEMBER_AMBIGUOUS
    assert len(exc.value.details["matches"]) == 2


def test_member_unique_partial():
    hit = resolve_member("Sam", MEMBERS)
    assert hit.id == "u-sam"


def test_work_item_by_key():
    hit = resolve_work_item("DEMO-108", ISSUES, project_identifier="DEMO")
    assert hit.id == "i2"
