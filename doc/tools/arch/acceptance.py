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
PLAN_TIER = re.compile(r"<!--\s*plan-tier:\s*([a-z]+)\s*-->")
PLAN_TIERS = ("micro", "standard", "full")
MICRO_MAX_LINES = 60
TIER_COMPLEXITY = {
    "micro": ("low",),
    "standard": ("low", "medium"),
    "full": ("low", "medium", "high", "critical"),
}
TIER_SECTIONS = {
    "micro": ("Приёмка", "Проверка"),
    "standard": ("Цель", "Приёмка", "Оценка", "Проверка"),
    "full": ("Цель", "Правила проекта", "Решения", "Риск", "Приёмка", "Оценка", "Проверка"),
}


def read_plan_tier(plan: Path) -> str | None:
    """Return the declared plan tier, or None when absent or unreadable."""
    try:
        match = PLAN_TIER.search(plan.read_text(encoding="utf-8"))
    except OSError:
        return None
    return match.group(1) if match else None


def plan_tier_problems(plan: Path, task: dict[str, Any], policy: dict[str, Any] | None = None) -> list[str]:
    """Check the declared plan tier against complexity and required sections.

    A marker is mandatory only once ``estimate_hours`` is set, so records that
    predate the tier contract keep their existing behaviour.
    """
    try:
        text = plan.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"plan.md: {exc}"]
    match = PLAN_TIER.search(text)
    if match is None:
        if task.get("estimate_hours") is not None:
            return ["plan.md: declare <!-- plan-tier: micro|standard|full --> when estimate_hours is set"]
        return []
    tier = match.group(1)
    tiers = (policy or {}).get("tiers") or {
        name: {"complexity": values, "required_sections": TIER_SECTIONS[name]}
        for name, values in TIER_COMPLEXITY.items()
    }
    if tier not in tiers:
        return [f"plan.md: unknown plan tier {tier!r}; use {', '.join(tiers)}"]
    selected = tiers[tier]
    complexity = task.get("complexity") or "low"
    allowed = selected.get("complexity") or TIER_COMPLEXITY.get(tier, ())
    if complexity not in allowed:
        return [
            f"plan.md: tier {tier!r} is not allowed for complexity {complexity!r}; "
            f"allowed: {', '.join(allowed)}"
        ]
    problems: list[str] = []
    headings = [line.lstrip("#").strip() for line in text.splitlines() if line.startswith("#")]
    required = selected.get("required_sections") or TIER_SECTIONS.get(tier, ())
    missing = [keyword for keyword in required if not any(keyword.casefold() in heading.casefold() for heading in headings)]
    if missing:
        problems.append(f"plan.md: tier {tier!r} requires sections: {', '.join(missing)}")
    limit = selected.get("max_nonempty_lines")
    if limit is not None:
        lines = sum(1 for line in text.splitlines() if line.strip())
        if lines > int(limit):
            problems.append(f"plan.md: {tier} plan has {lines} non-empty lines; limit is {limit}")
    return problems


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


def snapshot_status(root: Path, entries: Any, plan: Path) -> dict[str, Any]:
    """Classify recorded snapshot inputs against the current tree.

    ``missing`` means no usable manifest was recorded, ``stale`` means at least
    one recorded input differs or is gone, and ``current`` means every input
    still matches its recorded SHA-256.
    """
    if not isinstance(entries, list) or not entries:
        problems = ["snapshot_files must identify the verified files by SHA-256"]
        return {
            "status": "missing", "problems": problems,
            "stale_files": [], "missing_files": [],
        }
    problems: list[str] = []
    stale: list[str] = []
    missing: list[str] = []
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
                stale.append(path)
                problems.append(f"snapshot is stale: {path}")
        except (OSError, ValueError, RuntimeError) as exc:
            missing.append(path)
            problems.append(f"snapshot file {path}: {exc}")
    if plan.resolve() not in seen:
        problems.append("snapshot_files must include the stage plan")
    return {
        "status": "stale" if problems else "current",
        "problems": problems,
        "stale_files": sorted(set(stale)),
        "missing_files": sorted(set(missing)),
    }


def snapshot_problems(root: Path, entries: Any, plan: Path) -> list[str]:
    return snapshot_status(root, entries, plan)["problems"]


def _plan_policy_for(root: Any, task: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    """Resolve the type plan policy from either a ProjectConfig or a project root path."""
    if root is None or not task.get("task_type"):
        return None, []
    from .plan_policy import resolve_plan_policy
    from .project_config import ProjectConfig, load_project_config

    if isinstance(root, ProjectConfig):
        config = root
    else:
        config, errors = load_project_config(Path(root))
        if config is None:
            return None, errors
    if not (config.task_conf_root / "plan-defaults.yaml").is_file():
        return None, []
    return resolve_plan_policy(config, str(task["task_type"]))


def acceptance_state(
    root: Any, directory: Path, task: dict[str, Any], stage: str | None, *, check_evidence: bool = True,
) -> tuple[bool, list[str]]:
    """Return the plan readiness and closure blockers for an opted-in task.

    ``root`` may be a ``ProjectConfig`` or a project root ``Path``; both resolve the
    same type plan policy so the check cannot silently fall back to global defaults.
    """
    if stage is None:
        return False, ["acceptance: create a stage with a plan and verification.json"]
    path = directory / stage / "verification.json"
    try:
        if not (path.parent / "plan.md").is_file():
            raise ValueError("plan.md is missing")
        from .project_config import ProjectConfig
        root_path = root.root if isinstance(root, ProjectConfig) else Path(root)
        policy, policy_errors = _plan_policy_for(root, task)
        if policy_errors:
            raise ValueError("; ".join(policy_errors))
        if tier_problems := plan_tier_problems(path.parent / "plan.md", task, policy):
            raise ValueError("; ".join(tier_problems))
        evidence = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(evidence, dict) or evidence.get("task_key") != task.get("task_key") or evidence.get("stage_id") != stage:
            raise ValueError("verification.json must identify this task and stage")
        planned = planned_case_ids(evidence, criterion_ids(task))
        plan_text = (path.parent / "plan.md").read_text(encoding="utf-8")
        # Rules are part of the opt-in tier contract: a plan without a tier marker
        # keeps the pre-policy behaviour and is never judged by type rules.
        tier_match = PLAN_TIER.search(plan_text)
        if policy is not None and tier_match:
            from .plan_policy import evaluate_rules
            if rule_problems := evaluate_rules(
                plan_text, policy, case_count=len(planned), task=task,
                tier=tier_match.group(1),
            ):
                raise ValueError("; ".join(rule_problems))
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
        problems.extend(snapshot_problems(root_path, evidence.get("snapshot_files"), path.parent / "plan.md"))
    if task.get("phase") not in ("verification", "completed"):
        problems.append("task must be in verification before closure")
    return True, [f"acceptance {stage}: {problem}" for problem in problems]
