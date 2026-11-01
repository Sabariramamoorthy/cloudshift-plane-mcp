"""Ambiguity-safe entity resolution."""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from cloudshift.errors import CloudShiftError, CloudShiftErrorCode
from cloudshift.utils.normalization import display_name, normalize_name

_UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
_ISSUE_KEY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9]*)-(\d+)$")


def is_uuid(value: str) -> bool:
    if not _UUID_RE.match(value.strip()):
        return False
    try:
        uuid.UUID(value.strip())
        return True
    except ValueError:
        return False


@dataclass
class ResolveHit:
    id: str
    label: str
    raw: dict[str, Any]


def _unique_or_ambiguous(
    matches: list[ResolveHit],
    *,
    not_found: str,
    ambiguous: str,
    query: str,
) -> ResolveHit:
    if not matches:
        raise CloudShiftError(not_found, f"No match for {query!r}", {"query": query, "matches": []})
    if len(matches) > 1:
        raise CloudShiftError(
            ambiguous,
            f"Ambiguous match for {query!r}",
            {"query": query, "matches": [{"id": m.id, "label": m.label} for m in matches]},
        )
    return matches[0]


def resolve_entity(
    query: str,
    candidates: list[dict[str, Any]],
    *,
    id_key: str = "id",
    label_fn: Callable[[dict[str, Any]], str],
    identifier_keys: tuple[str, ...] = (),
    not_found: str,
    ambiguous: str,
) -> ResolveHit:
    q = (query or "").strip()
    if not q:
        raise CloudShiftError(CloudShiftErrorCode.VALIDATION_FAILED, "Empty resolution query")

    by_id = {str(c.get(id_key)): c for c in candidates if c.get(id_key)}
    if is_uuid(q) and q in by_id:
        c = by_id[q]
        return ResolveHit(id=str(c[id_key]), label=label_fn(c), raw=c)

    for key in identifier_keys:
        id_matches: list[ResolveHit] = []
        for c in candidates:
            ident = c.get(key)
            if ident is not None and str(ident).lower() == q.lower():
                id_matches.append(ResolveHit(id=str(c[id_key]), label=label_fn(c), raw=c))
        if id_matches:
            # De-dupe by id then require uniqueness
            uniq: dict[str, ResolveHit] = {m.id: m for m in id_matches}
            return _unique_or_ambiguous(
                list(uniq.values()),
                not_found=not_found,
                ambiguous=ambiguous,
                query=q,
            )

    nq = normalize_name(q)
    exact = []
    for c in candidates:
        label = label_fn(c)
        if normalize_name(label) == nq:
            exact.append(ResolveHit(id=str(c[id_key]), label=label, raw=c))
    if exact:
        return _unique_or_ambiguous(exact, not_found=not_found, ambiguous=ambiguous, query=q)

    ci = []
    for c in candidates:
        label = label_fn(c)
        if normalize_name(label) == nq:
            ci.append(ResolveHit(id=str(c[id_key]), label=label, raw=c))
    # already handled exact; case-insensitive equals is same as normalize_name

    partial = []
    for c in candidates:
        label = label_fn(c)
        nl = normalize_name(label)
        if nq and nq in nl:
            partial.append(ResolveHit(id=str(c[id_key]), label=label, raw=c))
    return _unique_or_ambiguous(partial, not_found=not_found, ambiguous=ambiguous, query=q)


def resolve_project(query: str, projects: list[dict[str, Any]]) -> ResolveHit:
    return resolve_entity(
        query,
        projects,
        label_fn=lambda p: p.get("name") or "",
        identifier_keys=("identifier",),
        not_found=CloudShiftErrorCode.PROJECT_NOT_FOUND,
        ambiguous=CloudShiftErrorCode.PROJECT_AMBIGUOUS,
    )


def resolve_member(query: str, members: list[dict[str, Any]]) -> ResolveHit:
    q = query.strip()
    nq = normalize_name(q)

    # Prefer exact full-name / email uniqueness; treat first-name-only collisions as ambiguous.
    first_name_hits = [
        ResolveHit(id=str(m["id"]), label=display_name(m), raw=m)
        for m in members
        if normalize_name(m.get("first_name") or "") == nq
    ]
    if len(first_name_hits) > 1:
        raise CloudShiftError(
            CloudShiftErrorCode.MEMBER_AMBIGUOUS,
            f"Ambiguous match for {q!r}",
            {"query": q, "matches": [{"id": m.id, "label": m.label} for m in first_name_hits]},
        )

    return resolve_entity(
        q,
        members,
        label_fn=display_name,
        identifier_keys=("email", "display_name"),
        not_found=CloudShiftErrorCode.MEMBER_NOT_FOUND,
        ambiguous=CloudShiftErrorCode.MEMBER_AMBIGUOUS,
    )


def resolve_module(query: str, modules: list[dict[str, Any]]) -> ResolveHit:
    return resolve_entity(
        query,
        modules,
        label_fn=lambda m: m.get("name") or "",
        not_found=CloudShiftErrorCode.MODULE_NOT_FOUND,
        ambiguous=CloudShiftErrorCode.MODULE_AMBIGUOUS,
    )


def resolve_cycle(query: str, cycles: list[dict[str, Any]]) -> ResolveHit:
    nq = normalize_name(query)
    # Convenience: "current sprint" / "current cycle" → unique active cycle by date if possible
    if nq in {"current sprint", "current cycle", "active sprint", "active cycle"}:
        active = [c for c in cycles if not c.get("archived_at")]
        hits = [ResolveHit(id=str(c["id"]), label=c.get("name") or "", raw=c) for c in active]
        return _unique_or_ambiguous(
            hits,
            not_found=CloudShiftErrorCode.CYCLE_NOT_FOUND,
            ambiguous=CloudShiftErrorCode.CYCLE_AMBIGUOUS,
            query=query,
        )
    return resolve_entity(
        query,
        cycles,
        label_fn=lambda c: c.get("name") or "",
        not_found=CloudShiftErrorCode.CYCLE_NOT_FOUND,
        ambiguous=CloudShiftErrorCode.CYCLE_AMBIGUOUS,
    )


def parse_issue_key(query: str) -> tuple[str, int] | None:
    m = _ISSUE_KEY_RE.match(query.strip())
    if not m:
        return None
    return m.group(1).upper(), int(m.group(2))


def resolve_work_item(
    query: str,
    issues: list[dict[str, Any]],
    *,
    project_identifier: str | None = None,
) -> ResolveHit:
    q = query.strip()
    if is_uuid(q):
        for issue in issues:
            if str(issue.get("id")) == q:
                return ResolveHit(id=q, label=issue.get("name") or q, raw=issue)
        raise CloudShiftError(CloudShiftErrorCode.WORK_ITEM_NOT_FOUND, f"No work item {q}", {"query": q})

    key = parse_issue_key(q)
    if key:
        ident, seq = key
        matches = [
            ResolveHit(id=str(i["id"]), label=i.get("name") or "", raw=i)
            for i in issues
            if int(i.get("sequence_id") or -1) == seq
            and (
                project_identifier is None
                or str(project_identifier).upper() == ident
                or str(i.get("project_identifier") or "").upper() == ident
            )
        ]
        # If project_identifier not on issue, filter only by sequence when single project context
        if not matches and project_identifier and str(project_identifier).upper() == ident:
            matches = [
                ResolveHit(id=str(i["id"]), label=i.get("name") or "", raw=i)
                for i in issues
                if int(i.get("sequence_id") or -1) == seq
            ]
        return _unique_or_ambiguous(
            matches,
            not_found=CloudShiftErrorCode.WORK_ITEM_NOT_FOUND,
            ambiguous=CloudShiftErrorCode.WORK_ITEM_AMBIGUOUS,
            query=q,
        )

    return resolve_entity(
        q,
        issues,
        label_fn=lambda i: i.get("name") or "",
        not_found=CloudShiftErrorCode.WORK_ITEM_NOT_FOUND,
        ambiguous=CloudShiftErrorCode.WORK_ITEM_AMBIGUOUS,
    )
