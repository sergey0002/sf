"""Check declared acceptance cases and the evidence needed to close a task."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

CASE_COVERAGE = "case-coverage-v1"
CRITERION = re.compile(r"^(AC-[1-9][0-9]*):\s*\S")
CASE_ID = re.compile(r"^CASE-[1-9][0-9]*$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def criterion_ids(task: dict[str, Any]) -> set[str]:
    criteria = task.get("acceptance_criteria")
    if not isinstance(criteria, list) or not criteria:
        raise ValueError("acceptance_criteria must contain at least one AC-N")
    ids = set()
    for item in criteria:
        match = CRITERION.match(item) if isinstance(item, str) else None
        if not match or match[1] in ids:
            raise ValueError("acceptance_criteria must use unique 'AC-N: observable outcome' entries")
        ids.add(match[1])
    return ids


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def planned_case_ids(evidence: dict[str, Any], criteria: set[str]) -> set[str]:
    planned = evidence.get("planned_checks")
    if not isinstance(planned, list) or not planned:
        raise ValueError("planned_checks must declare at least one case")
    cases = set()
    covered = set()
    for entry in planned:
        case = entry.get("id") if isinstance(entry, dict) else None
        if not isinstance(case, str) or not CASE_ID.fullmatch(case) or case in cases:
            raise ValueError("planned_checks must use unique CASE-N IDs")
        covers = entry.get("covers")
        if (not isinstance(covers, list) or not covers
                or any(not isinstance(ac, str) or ac not in criteria for ac in covers)):
            raise ValueError(f"{case}: covers must reference existing AC IDs")
        if not _text(entry.get("expected")):
            raise ValueError(f"{case}: expected outcome is missing")
        cases.add(case)
        covered.update(covers)
    if missing := criteria - covered:
        raise ValueError(f"missing planned cases for {', '.join(sorted(missing))}")
    return cases


def snapshot_file(root: Path, name: str) -> tuple[Path, str]:
    relative = Path(name)
    target = (root / relative).resolve()
    if relative.is_absolute() or ".." in relative.parts or not target.is_relative_to(root):
        raise ValueError("path escapes the project")
    if not target.is_file():
        raise ValueError("path is missing or not a regular file")
    with target.open("rb") as source:
        checksum = hashlib.sha256()
        for block in iter(lambda: source.read(65536), b""):
            checksum.update(block)
    return target, checksum.hexdigest()


def snapshot_problems(root: Path, entries: Any, plan: Path) -> list[str]:
    if not isinstance(entries, list) or not entries:
        return ["snapshot_files must identify the verified files by SHA-256"]
    problems = []
    seen = set()
    for entry in entries:
        path = entry.get("path") if isinstance(entry, dict) else None
        digest = entry.get("sha256") if isinstance(entry, dict) else None
        if not _text(path) or not isinstance(digest, str) or not SHA256.fullmatch(digest):
            problems.append("snapshot_files requires project-relative paths and SHA-256 digests")
            continue
        try:
            target, actual = snapshot_file(root, path)
            if target in seen:
                raise ValueError("path is duplicate")
            seen.add(target)
            if actual != digest:
                problems.append(f"snapshot is stale: {path}")
        except (OSError, ValueError, RuntimeError) as exc:
            problems.append(f"snapshot file {path}: {exc}")
    if plan.resolve() not in seen:
        problems.append("snapshot_files must include the stage plan")
    return problems


def acceptance_state(
    root: Path, directory: Path, task: dict[str, Any], stage: str | None, *, check_evidence: bool = True,
) -> tuple[bool, list[str]]:
    """Return the plan readiness and closure blockers for an opted-in task."""
    if stage is None:
        return False, ["acceptance: create a stage with a plan and verification.json"]
    path = directory / stage / "verification.json"
    try:
        if not (path.parent / "plan.md").is_file():
            raise ValueError("plan.md is missing")
        evidence = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(evidence, dict) or evidence.get("task_key") != task.get("task_key") or evidence.get("stage_id") != stage:
            raise ValueError("verification.json must identify this task and stage")
        planned = planned_case_ids(evidence, criterion_ids(task))
    except (OSError, ValueError) as exc:
        return False, [f"acceptance {stage}: {exc}"]
    if not check_evidence:
        return True, []

    problems = []
    observations = {}
    checks = evidence.get("checks", [])
    if not isinstance(checks, list):
        checks = []
        problems.append("checks must be an array")
    for check in checks:
        cases = check.get("cases", []) if isinstance(check, dict) else None
        if not isinstance(cases, list) or any(not isinstance(case, str) or case not in planned for case in cases):
            problems.append("a check references an invalid or undeclared case")
            continue
        passed = (type(check.get("exit_code")) is int and check["exit_code"] == 0
                  and _text(check.get("command")) and _text(check.get("result")))
        for case in cases:
            observations[case] = passed
    if missing := {case for case in planned if not observations.get(case)}:
        problems.append(f"cases without a passing result: {', '.join(sorted(missing))}")
    if evidence.get("status") != "passed" or not _text(evidence.get("checked_revision")):
        problems.append("verification requires status passed and checked_revision")
    else:
        problems.extend(snapshot_problems(root, evidence.get("snapshot_files"), path.parent / "plan.md"))
    if task.get("phase") not in ("verification", "completed"):
        problems.append("task must be in verification before closure")
    return True, [f"acceptance {stage}: {problem}" for problem in problems]
