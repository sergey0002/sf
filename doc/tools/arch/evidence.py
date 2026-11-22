"""Capture a test result on an explicitly selected, stable task snapshot."""

from __future__ import annotations

import hashlib
import json
import shlex
import subprocess
from pathlib import Path
from typing import Any

from .acceptance import CASE_COVERAGE, criterion_ids, planned_case_ids, snapshot_file, snapshot_problems
from .fs_atomic import write_json_record
from .project_config import ProjectConfig
from .subtask import current_stage, list_stages
from .task_ops import _task_writer, task_or_subtask_paths


def _files(root: Path, names: list[str], excluded: set[Path]) -> list[dict[str, str]]:
    records = {}
    for name in names:
        path, digest = snapshot_file(root, name)
        if path in excluded:
            raise ValueError("task.json and verification.json are mutable records, not snapshot inputs")
        records[path.relative_to(root).as_posix()] = digest
    return [{"path": path, "sha256": digest} for path, digest in sorted(records.items())]


def task_evidence(
    config: ProjectConfig, key: str, *, names: list[str], cases: list[str], argv: list[str] | None,
    replace_snapshot: bool,
) -> tuple[dict[str, Any], int]:
    directory, task_path = task_or_subtask_paths(config, key)
    stage = current_stage(list_stages(directory))
    if stage is None:
        raise ValueError(f"{key}: no current stage")
    artifact = directory / stage / "verification.json"
    plan = directory / stage / "plan.md"
    root = config.root
    if not artifact.resolve().is_relative_to(directory.resolve()):
        raise ValueError("verification.json escapes the task directory")
    original = artifact.read_bytes()
    data = json.loads(original)
    if not isinstance(data, dict) or data.get("task_key") != key or data.get("stage_id") != stage:
        raise ValueError("verification.json must identify this task and stage")
    result: dict[str, Any] = {"task_key": key, "stage_id": stage,
                             "verification": artifact.relative_to(root).as_posix()}
    if argv is None:
        problems = snapshot_problems(root, data.get("snapshot_files"), plan)
        result.update(current=not problems, problems=problems)
        return result, int(bool(problems))
    if not names or not argv:
        raise ValueError("--run requires a command and at least one explicit --file")

    task_bytes = task_path.read_bytes()
    task = json.loads(task_bytes)
    if not isinstance(task, dict) or task.get("task_key") != key:
        raise ValueError("task.json must identify this task")
    planned = planned_case_ids(data, criterion_ids(task)) if task.get("acceptance_policy") == CASE_COVERAGE else set()
    if set(cases) - planned:
        raise ValueError("--case must refer to a planned case in verification.json")
    cases = list(dict.fromkeys(cases))
    selected = [*names, plan.relative_to(root).as_posix()]
    excluded = {artifact.resolve(), task_path.resolve()}
    snapshot = _files(root, selected, excluded)
    checks = data.get("checks", [])
    if not isinstance(checks, list) or any(
        not isinstance(check, dict) or not isinstance(check.get("cases", []), list)
        or any(not isinstance(case, str) for case in check.get("cases", []))
        for check in checks
    ):
        raise ValueError("verification.json checks must be objects with optional case arrays")
    previous = data.get("snapshot_files", [])
    same_snapshot = isinstance(previous, list) and all(isinstance(item, dict) for item in previous)
    same_snapshot = same_snapshot and sorted(previous, key=lambda item: str(item.get("path"))) == snapshot
    if checks and not same_snapshot:
        if not replace_snapshot:
            raise ValueError("evidence is for another snapshot; rerun with --replace-snapshot to start fresh")
        checks = []

    process = subprocess.run(argv, cwd=root, capture_output=True, text=True, errors="replace", check=False)
    code = process.returncode if process.returncode >= 0 else 128 - process.returncode
    command = shlex.join(argv)
    check = {"command": command, "exit_code": code, "cases": cases,
             "result": f"Command exited with status {code}."}
    if code:
        result["output_tail"] = (process.stdout + "\n" + process.stderr).strip()[-2048:]
    result.update(exit_code=code, cases=cases)

    with _task_writer(config, directory):
        if (current_stage(list_stages(directory)) != stage or artifact.read_bytes() != original
                or task_path.read_bytes() != task_bytes or _files(root, selected, excluded) != snapshot):
            raise ValueError("task, evidence or selected files changed during the run; result was not recorded")
        checks = [item for item in checks if (item.get("command"), item.get("cases", [])) != (command, cases)]
        checks.append(check)
        latest = {case: item.get("exit_code") for item in checks for case in item.get("cases", [])}
        failed = any(case in latest and latest[case] != 0 for case in planned) or any(
            item.get("exit_code") != 0 for item in checks if not item.get("cases"))
        complete = all(latest.get(case) == 0 for case in planned)
        revision = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode("utf-8")).hexdigest()
        data.update(checks=checks, snapshot_files=snapshot, checked_revision=f"sha256:{revision}",
                    status="failed" if failed else "passed" if complete else "not_run")
        write_json_record(artifact, data)
    result["status"] = data["status"]
    return result, code
