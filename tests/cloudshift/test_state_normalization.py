from cloudshift.utils.states import NormalizedState, classify_issue_state, classify_state_group


def test_group_mapping():
    assert classify_state_group("backlog") == NormalizedState.BACKLOG
    assert classify_state_group("unstarted") == NormalizedState.TODO
    assert classify_state_group("started") == NormalizedState.IN_PROGRESS
    assert classify_state_group("completed") == NormalizedState.COMPLETED
    assert classify_state_group("cancelled") == NormalizedState.CANCELLED
    assert classify_state_group("weird") == NormalizedState.UNKNOWN


def test_classify_from_expanded_state():
    issue = {"state": {"id": "x", "group": "started", "name": "In Progress"}}
    assert classify_issue_state(issue, {}) == NormalizedState.IN_PROGRESS


def test_classify_from_state_id():
    states = {"s1": {"id": "s1", "group": "completed"}}
    assert classify_issue_state({"state": "s1"}, states) == NormalizedState.COMPLETED
