"""Application-layer scenarios for the task lifecycle.

This module owns deterministic reads, validation and writes for ``task.json``
records. It knows nothing about ``argparse`` or CLI output: commands translate
returned payloads and :class:`TaskOpsError` into envelopes.

Composite writes (decompose) validate the whole package before touching disk,
record their intent in a journal, and can be resumed after an interruption.
"""

from __future__ import annotations

import json
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .acceptance import CASE_COVERAGE, acceptance_state
from .cli.errors import EXIT_CONFLICT, EXIT_ERROR, EXIT_NOT_FOUND
from .constants import TASK_KEY_RE, TASK_NUMBER_RE
from .fs_atomic import (
    JournalError, WriterBusyError, clear_journal, journal_path, lock_directory,
    read_journal, stale_write_temps, write_journal, write_json_record,
)
from .identity import task_dir
from .project_config import ProjectConfig
from .schema import scaffold_task_json
from .subtask import (
    current_stage,
    list_stages,
    list_sub_subtasks,
    scaffold_subtask_json,
    subtask_dir,
)
from .validation import inspect_subtasks, validate_task_json

TASK_MD_ERROR = "task.md exists; manifest requires task.json as the only canonical input"


class TaskOpsError(Exception):
    """A deterministic lifecycle failure that a command renders as an envelope."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        field: str | None = None,
        suggestion: str | None = None,
        exit_code: int = EXIT_ERROR,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field
        self.suggestion = suggestion
        self.exit_code = exit_code


def task_paths(project_config: ProjectConfig, task_key: str) -> tuple[Path, Path]:
    tdir = task_dir(project_config, task_key)
    return tdir, tdir / "task.json"


SUBTASK_KEY_RE = re.compile(r"^(?P<parent>[A-Z][A-Z0-9]{0,7}-\d{4}|\d{4})-(?P<id>\d{4})$")


def task_or_subtask_paths(project_config: ProjectConfig, key: str) -> tuple[Path, Path]:
    """Resolve a parent task key or a ``<parent>-<subtask_id>`` key."""
    match = SUBTASK_KEY_RE.fullmatch(key)
    if match:
        return _subtask_paths(project_config, match.group("parent"), match.group("id"))
    return task_paths(project_config, key)


def _relative(path: Path, project_config: ProjectConfig) -> str:
    return path.relative_to(project_config.root).as_posix()


def load_task(
    project_config: ProjectConfig,
    task_key: str,
    *,
    invalid_message: str = "cannot read task.json",
) -> dict[str, Any]:
    """Read a task record, raising a structured error when absent or malformed."""
    _, tjson = task_paths(project_config, task_key)
    try:
        data = json.loads(tjson.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise TaskOpsError(
            "NOT-FOUND",
            f"task.json not found: {_relative(tjson, project_config)}",
            field="task_key",
            suggestion=f"create it: arch task init {task_key}",
            exit_code=EXIT_NOT_FOUND,
        ) from None
    except (ValueError, OSError) as exc:
        raise TaskOpsError(
            "INVALID",
            f"{invalid_message}: {exc}",
            field="task.json",
            suggestion=f"check {_relative(tjson, project_config)}",
        ) from None
    if not isinstance(data, dict):
        raise TaskOpsError(
            "INVALID",
            f"{invalid_message}: task.json must be a JSON object",
            field="task.json",
            suggestion=f"check {_relative(tjson, project_config)}",
        )
    return data


def validation_errors(
    project_config: ProjectConfig, tdir: Path, data: dict[str, Any], task_key: str
) -> list[str]:
    errors = validate_task_json(data, task_key, project_config)
    if (tdir / "task.md").exists():
        errors.append(TASK_MD_ERROR)
    return errors


def pending_write(tdir: Path) -> dict[str, Any] | None:
    """Return a human-readable summary of an interrupted composite write."""
    try:
        journal = read_journal(tdir)
    except JournalError as exc:
        return {
            "kind": "decompose", "state": "invalid", "path": journal_path(tdir).name,
            "message": f"Invalid write journal {journal_path(tdir).name}: {exc}; inspect before retrying",
        }
    if journal is None:
        return None
    kind = journal.get("kind", "unknown")
    task_key = journal.get("task_key")
    ids = [
        entry.get("id")
        for entry in journal.get("subtasks", [])
        if isinstance(entry, dict) and entry.get("id")
    ]
    scope = f" for {task_key}" if task_key else ""
    ids_part = f" ({', '.join(ids)})" if ids else ""
    return {
        "kind": kind,
        "task_key": task_key,
        "subtask_ids": ids,
        "path": journal_path(tdir).name,
        "message": (
            f"Incomplete {kind} write{scope}{ids_part}: journal "
            f"{journal_path(tdir).name} is present; rerun the same command to resume"
        ),
    }


@contextmanager
def _task_writer(project_config: ProjectConfig, tdir: Path):
    try:
        with lock_directory(tdir):
            yield
    except WriterBusyError as exc:
        raise TaskOpsError(
            "CONFLICT", f"another task writer is active: {_relative(tdir, project_config)}",
            field="task_key", exit_code=EXIT_CONFLICT,
            suggestion="retry after the active task operation finishes",
        ) from exc


def _assert_subtasks_directory(tdir: Path) -> None:
    directory = tdir / "subtasks"
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise TaskOpsError("CONFLICT", "subtasks must be a local directory", field="subtasks",
                           exit_code=EXIT_CONFLICT)


# ---------------------------------------------------------------------------
# Read-only scenarios
# ---------------------------------------------------------------------------


def init_task(
    project_config: ProjectConfig,
    task_key: str,
    task_number: str,
    source_type: str,
    source_prefix: str | None,
) -> dict[str, Any]:
    tdir, tjson = task_paths(project_config, task_key)
    try:
        tdir.mkdir()
    except FileExistsError:
        raise TaskOpsError(
            "CONFLICT",
            f"task directory already exists: {_relative(tdir, project_config)}",
            field="task_key",
            exit_code=EXIT_CONFLICT,
            suggestion=f"use a different task key or remove {_relative(tdir, project_config)}",
        )
    stage_dir = tdir / "stage1"
    try:
        stage_dir.mkdir(parents=True, exist_ok=True)
        write_json_record(
            tjson,
            json.loads(scaffold_task_json(task_key, task_number, source_type, source_prefix)),
        )
    except OSError as exc:
        tjson.unlink(missing_ok=True)
        try:
            stage_dir.rmdir()
            tdir.rmdir()
        except OSError:
            pass
        raise TaskOpsError(
            "WRITE",
            f"cannot write task record: {exc}",
            field="task.json",
            suggestion=f"check permissions for {_relative(tdir, project_config)}",
        ) from None
    return {
        "ok": True,
        "task_key": task_key,
        "task_number": task_number,
        "source_type": source_type,
        "source_prefix": source_prefix,
        "directory": _relative(tdir, project_config),
        "task_json": _relative(tjson, project_config),
        "stage_dir": _relative(stage_dir, project_config),
    }


def workspace_info(
    project_config: ProjectConfig, task_key: str, task_number: str, source_type: str
) -> tuple[dict[str, Any], list[str]]:
    tdir, tjson = task_paths(project_config, task_key)
    data = load_task(project_config, task_key)
    errors = validation_errors(project_config, tdir, data, task_key)
    if errors:
        return {}, errors
    return {
        "ok": True,
        "task_key": task_key,
        "task_number": task_number,
        "directory": _relative(tdir, project_config),
        "task_json": _relative(tjson, project_config),
        "target_release": data.get("target_release", "unset"),
        "branch_hint": (
            f"futures/{task_number}" if source_type == "jira" else f"bugfix/{task_key}"
        ),
        "note": "workspace preparation is deterministic; actual git checkout requires configured repository",
    }, []


def status_info(
    project_config: ProjectConfig,
    task_key: str,
    task_number: str,
    source_type: str,
    source_prefix: str | None,
) -> dict[str, Any]:
    tdir, tjson = task_paths(project_config, task_key)
    data = load_task(project_config, task_key)
    stages = list_stages(tdir)
    verification_files = [
        _relative(tdir / stage / "verification.json", project_config)
        for stage in stages
        if (tdir / stage / "verification.json").exists()
    ]
    result = {
        "task_key": task_key,
        "task_number": task_number,
        "source_type": source_type,
        "source_prefix": source_prefix,
        "directory": _relative(tdir, project_config),
        "task_json": _relative(tjson, project_config),
        "stages": stages,
        "verification_files": verification_files,
        "has_task_md": (tdir / "task.md").exists(),
        "target_release": data.get("target_release", "unset"),
        "task_type": data.get("task_type", "unset"),
        "flow": data.get("flow", "unset"),
        "complexity": data.get("complexity", "unset"),
        "phase": data.get("phase", "unset"),
    }
    pending = pending_write(tdir)
    if pending is not None:
        result["incomplete_write"] = pending
    return result


# ---------------------------------------------------------------------------
# Composite write: decompose
# ---------------------------------------------------------------------------


def _planned_subtasks(
    task_key: str, subtask_ids: list[str], subtask_titles: list[str]
) -> list[dict[str, str]]:
    if len(subtask_ids) != len(subtask_titles):
        raise TaskOpsError(
            "ARGS",
            "--subtask-id and --subtask-title must be provided in equal numbers",
            field="subtask",
            suggestion="provide the same number of --subtask-id and --subtask-title flags",
        )
    planned: list[dict[str, str]] = []
    seen: set[str] = set()
    for subtask_id, title in zip(subtask_ids, subtask_titles):
        if not TASK_NUMBER_RE.fullmatch(subtask_id):
            raise TaskOpsError(
                "ARGS",
                f"subtask_id must be exactly four decimal digits, got {subtask_id!r}",
                field="subtask_id",
            )
        if subtask_id in seen:
            raise TaskOpsError(
                "CONFLICT",
                f"duplicate subtask id in package: {subtask_id}",
                field="subtask_id",
                exit_code=EXIT_CONFLICT,
                suggestion="provide each subtask id once",
            )
        if not title.strip():
            raise TaskOpsError(
                "ARGS",
                f"subtask title must be non-empty for id {subtask_id}",
                field="subtask_title",
            )
        seen.add(subtask_id)
        planned.append({"id": subtask_id, "title": title})
    return planned


def _check_package_collisions(
    project_config: ProjectConfig,
    tdir: Path,
    task_key: str,
    data: dict[str, Any],
    planned: list[dict[str, str]],
) -> None:
    declared = {
        record.get("id")
        for record in data.get("subtasks", [])
        if isinstance(record, dict)
    }
    for entry in planned:
        subtask_id = entry["id"]
        if subtask_id in declared:
            raise TaskOpsError(
                "CONFLICT",
                f"subtask {subtask_id} is already declared in task.json",
                field="subtask_id",
                exit_code=EXIT_CONFLICT,
                suggestion=f"use a different --subtask-id or update the existing subtask {subtask_id}",
            )
        stdir = subtask_dir(project_config, task_key, subtask_id)
        if stdir.exists() or stdir.is_symlink():
            raise TaskOpsError(
                "CONFLICT",
                f"subtask directory already exists: {_relative(stdir, project_config)}",
                field="subtask_id",
                exit_code=EXIT_CONFLICT,
                suggestion=f"use a different --subtask-id or remove {_relative(stdir, project_config)}",
            )


def _verify_resumed_child(
    project_config: ProjectConfig, stdir: Path, subtask_key: str, title: str
) -> bool:
    """Check an existing child from an interrupted run.

    Returns True when the directory was created but its record is still missing,
    which is safe to finish because the journal owns this package.
    """
    stjson = stdir / "task.json"
    stage = stdir / "stage1"
    if (stdir.is_symlink() or not stdir.is_dir() or stjson.is_symlink()
            or stage.is_symlink() or (stage.exists() and not stage.is_dir())):
        raise TaskOpsError("CONFLICT", f"unexpected entry for subtask {subtask_key}",
                           field="subtask_id", exit_code=EXIT_CONFLICT)
    if not stjson.exists():
        allowed = stale_write_temps(stjson) | {stage}
        unexpected = sorted(entry.name for entry in stdir.iterdir() if entry not in allowed)
        if unexpected:
            raise TaskOpsError(
                "CONFLICT",
                f"cannot resume subtask {subtask_key}: unexpected entries in "
                f"{_relative(stdir, project_config)}: {', '.join(unexpected)}",
                field="subtask_id",
                exit_code=EXIT_CONFLICT,
                suggestion=f"inspect {_relative(stdir, project_config)} before retrying",
            )
        return True
    try:
        existing = json.loads(stjson.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise TaskOpsError(
            "CONFLICT",
            f"cannot resume subtask {subtask_key}: {exc}",
            field="subtask_id",
            exit_code=EXIT_CONFLICT,
            suggestion=f"inspect {_relative(stdir, project_config)}",
        ) from None
    if not isinstance(existing, dict) or existing.get("task_key") != subtask_key:
        raise TaskOpsError(
            "CONFLICT",
            f"directory {_relative(stdir, project_config)} does not belong to subtask {subtask_key}",
            field="subtask_id",
            exit_code=EXIT_CONFLICT,
            suggestion=f"inspect {_relative(stdir, project_config)} before retrying",
        )
    if existing.get("title") != title:
        raise TaskOpsError(
            "CONFLICT",
            f"subtask {subtask_key} exists with a different title",
            field="subtask_title",
            exit_code=EXIT_CONFLICT,
            suggestion="rerun with the recorded title or inspect the existing record",
        )
    return False


def decompose(
    project_config: ProjectConfig,
    task_key: str,
    subtask_ids: list[str],
    subtask_titles: list[str],
) -> dict[str, Any]:
    """Serialize writes to the parent and validate the whole package before writing."""
    tdir, tjson = task_paths(project_config, task_key)
    if not tdir.is_dir():
        load_task(project_config, task_key)  # Preserve the public not-found result.
    with _task_writer(project_config, tdir):
        return _decompose_locked(project_config, task_key, tdir, tjson, subtask_ids, subtask_titles)


def _decompose_locked(
    project_config: ProjectConfig, task_key: str, tdir: Path, tjson: Path,
    subtask_ids: list[str], subtask_titles: list[str],
) -> dict[str, Any]:
    data = load_task(project_config, task_key)
    if (tdir / "task.md").exists():
        raise TaskOpsError(
            "VALIDATION",
            TASK_MD_ERROR,
            field="task.json",
            suggestion=f"remove {_relative(tdir / 'task.md', project_config)} before decomposing",
        )
    if not isinstance(data.get("subtasks", []), list):
        raise TaskOpsError(
            "VALIDATION",
            "task.json: subtasks must be an array",
            field="task.json",
            suggestion=f"fix {_relative(tjson, project_config)} before decomposing",
        )

    planned = _planned_subtasks(task_key, subtask_ids, subtask_titles)
    journal_file = journal_path(tdir)
    try:
        journal = read_journal(tdir)
    except JournalError as exc:
        raise TaskOpsError(
            "CONFLICT", f"Invalid write journal {journal_file.name}: {exc}", field="subtasks",
            exit_code=EXIT_CONFLICT, suggestion="inspect the journal and records before retrying",
        ) from exc
    if journal is not None and journal["subtasks"] != planned:
        raise TaskOpsError(
            "CONFLICT", "incomplete decompose journal records a different package", field="subtask",
            exit_code=EXIT_CONFLICT, suggestion="rerun decompose with the recorded package",
        )
    if not planned:
        return {"ok": True, "task_key": task_key, "subtasks_created": []}

    _assert_subtasks_directory(tdir)
    if journal is None:
        _check_package_collisions(project_config, tdir, task_key, data, planned)

    declared = data.get("subtasks", [])
    targets = []
    new_records = []
    for entry in planned:
        subtask_id, title = entry["id"], entry["title"]
        subtask_key = f"{task_key}-{subtask_id}"
        stdir = subtask_dir(project_config, task_key, subtask_id)
        needs_write = True
        if journal is not None and (stdir.exists() or stdir.is_symlink()):
            needs_write = _verify_resumed_child(project_config, stdir, subtask_key, title)
        path = f"subtasks/{subtask_id}/task.json"
        matches = [record for record in declared if isinstance(record, dict) and record.get("id") == subtask_id]
        if matches and (len(matches) != 1 or matches[0].get("title") != title or matches[0].get("path") != path):
            raise TaskOpsError("CONFLICT", f"parent declares a different record for subtask {subtask_id}",
                               field="subtasks", exit_code=EXIT_CONFLICT)
        if not matches:
            new_records.append({"id": subtask_id, "title": title, "status": "open", "path": path})
        targets.append((stdir, needs_write, entry))

    # No changes, including temporary-file cleanup, before the whole preflight passes.
    created: list[dict[str, str]] = []
    try:
        if journal is None:
            write_journal(tdir, {"schema_version": 1, "kind": "decompose", "task_key": task_key, "subtasks": planned})
        temps = stale_write_temps(tjson) | stale_write_temps(journal_file)
        for stdir, needs_write, entry in targets:
            stjson = stdir / "task.json"
            temps.update(stale_write_temps(stjson))
            if needs_write:
                (stdir / "stage1").mkdir(parents=True, exist_ok=True)
                write_json_record(stjson, json.loads(scaffold_subtask_json(task_key, entry["id"], entry["title"])))
            created.append({
                "subtask_id": entry["id"], "title": entry["title"],
                "directory": _relative(stdir, project_config), "task_json": _relative(stjson, project_config),
            })
        if new_records:
            data["subtasks"] = declared + new_records
            write_json_record(tjson, data)
        for path in temps:
            path.unlink(missing_ok=True)
        clear_journal(tdir)
    except OSError as exc:
        raise TaskOpsError(
            "WRITE",
            f"decompose interrupted: {exc}",
            field="task.json",
            suggestion=(
                f"rerun `arch task decompose {task_key} ...` with the same package to resume; "
                f"journal: {_relative(journal_path(tdir), project_config)}"
            ),
        ) from None

    return {"ok": True, "task_key": task_key, "subtasks_created": created}


# ---------------------------------------------------------------------------
# Closure and diagnosis
# ---------------------------------------------------------------------------


def _dependency_path(config: ProjectConfig, key: str) -> Path:
    parent = key
    children = []
    while not TASK_KEY_RE.fullmatch(parent):
        parent, separator, child = parent.rpartition("-")
        if not separator or not TASK_NUMBER_RE.fullmatch(child):
            raise ValueError("invalid task or subtask key")
        children.append(child)
    path = task_dir(config, parent)
    for child in reversed(children):
        path = path / "subtasks" / child
    path = path / "task.json"
    if not path.resolve().is_relative_to(config.tasks_root):
        raise ValueError("dependency escapes the configured tasks root")
    return path


def dependency_state(config: ProjectConfig, task_key: str, task: dict[str, Any]) -> tuple[list[dict], list[str]]:
    """Resolve task/subtask references, including prerequisites of completed dependencies."""
    rows = []
    blockers = []
    checked = set()

    def visit(owner: str, data: dict, lineage: tuple[str, ...]) -> None:
        keys = data.get("depends_on", [])
        if not isinstance(keys, list):
            blockers.append(f"Dependency list for {owner} must be an array")
            return
        for key in keys:
            if not isinstance(key, str):
                blockers.append(f"Dependency of {owner} must be a task key")
                continue
            if key in lineage:
                blockers.append(f"Dependency cycle: {' -> '.join((*lineage, key))}")
                continue
            if key in checked:
                continue
            checked.add(key)
            row = {"task_key": key, "required_by": owner}
            rows.append(row)
            try:
                path = _dependency_path(config, key)
                dep = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(dep, dict) or dep.get("task_key") != key:
                    raise ValueError("task.json key does not match the dependency")
                phase = dep.get("phase")
                if not isinstance(phase, str) or not phase:
                    raise ValueError("task.json has no valid phase")
            except FileNotFoundError:
                row["state"] = "missing"
                blockers.append(f"Dependency {key}: task.json missing")
                continue
            except (OSError, ValueError, RuntimeError) as exc:
                row["state"] = "invalid"
                blockers.append(f"Dependency {key}: {exc}")
                continue
            row["phase"] = phase
            if phase != "completed":
                row["state"] = "open"
                blockers.append(f"Dependency {key}: phase is {phase!r}, expected completed")
            else:
                row["state"] = "completed"
                visit(key, dep, (*lineage, key))

    visit(task_key, task, (task_key,))
    return rows, list(dict.fromkeys(blockers))


def closure_state(
    project_config: ProjectConfig, tdir: Path, task_key: str, data: dict[str, Any], stage: str | None,
) -> tuple[list[dict[str, Any]], list[str], list[str], dict[str, Any] | None, bool | None, list[dict]]:
    """Return the same immediate-child facts for diagnosis and closure."""
    children, subtask_errors = inspect_subtasks(tdir, data, project_root=project_config.root)
    blockers = validation_errors(project_config, tdir, data, task_key) + subtask_errors
    dependencies, dependency_blockers = dependency_state(project_config, task_key, data)
    blockers.extend(dependency_blockers)
    plan_ready = None
    if data.get("acceptance_policy") == CASE_COVERAGE:
        plan_ready, evidence_problems = acceptance_state(project_config.root, tdir, data, stage)
        blockers.extend(evidence_problems)
    pending = pending_write(tdir)
    if pending is not None:
        blockers = [pending["message"]] + blockers
    return children, subtask_errors, blockers, pending, plan_ready, dependencies


def diagnose(
    project_config: ProjectConfig, task_key: str, task_number: str, source_type: str, brief: bool
) -> dict[str, Any]:
    tdir, tjson = task_paths(project_config, task_key)
    data = load_task(project_config, task_key)
    stages = list_stages(tdir)
    current = current_stage(stages)
    subtasks, subtask_errors, blockers, pending, plan_ready, dependencies = closure_state(
        project_config, tdir, task_key, data, current
    )
    closed_count = sum(subtask["phase"] == "completed" for subtask in subtasks)
    result: dict[str, Any] = {
        "task_key": task_key,
        "task_number": task_number,
        "source_type": source_type,
        "task_type": data.get("task_type"),
        "flow": data.get("flow"),
        "complexity": data.get("complexity"),
        "phase": data.get("phase"),
        "all_subtasks_closed": not subtask_errors,
        "can_close": not blockers,
        "close_blockers": blockers[:3] if brief else blockers,
        "stages": stages,
        "subtask_count": len(subtasks),
        "subtask_closed_count": closed_count,
    }
    if pending is not None:
        result["incomplete_write"] = pending
    if plan_ready is not None:
        result["acceptance_plan_ready"] = plan_ready
    if dependencies:
        result["dependencies"] = dependencies[:3] if brief else dependencies
        if brief and len(dependencies) > 3:
            result["dependencies_truncated"] = True
    if brief:
        refs = {"task": _relative(tjson, project_config)}
        if current:
            for key, filename in (("plan", "plan.md"), ("verification", "verification.json")):
                artifact = tdir / current / filename
                if artifact.is_file():
                    refs[key] = _relative(artifact, project_config)
        result.update(
            refs=refs,
            blocker_count=len(blockers),
            blockers_truncated=len(blockers) > 3,
        )
    else:
        result["subtasks"] = subtasks
    return result


def close(
    project_config: ProjectConfig, task_key: str, dry_run: bool
) -> tuple[dict[str, Any], list[str]]:
    tdir, tjson = task_paths(project_config, task_key)
    if dry_run or not tdir.is_dir():
        return _close_task(project_config, task_key, tdir, tjson, dry_run)
    with _task_writer(project_config, tdir):
        return _close_task(project_config, task_key, tdir, tjson, dry_run)


def _close_task(project_config: ProjectConfig, task_key: str, tdir: Path, tjson: Path,
                dry_run: bool) -> tuple[dict[str, Any], list[str]]:
    data = load_task(project_config, task_key)
    _, _, blockers, _, _, _ = closure_state(
        project_config, tdir, task_key, data, current_stage(list_stages(tdir))
    )
    if dry_run:
        return {"would_close": not blockers, "task_key": task_key, "blockers": blockers}, blockers
    if blockers:
        return {}, blockers
    data["phase"] = "completed"
    try:
        write_json_record(tjson, data)
    except OSError as exc:
        raise TaskOpsError(
            "WRITE",
            f"cannot close task {task_key}: {exc}",
            field="task.json",
            suggestion=f"check permissions for {_relative(tjson, project_config)}",
        ) from None
    return {"ok": True, "task_key": task_key, "phase": "completed"}, []


# ---------------------------------------------------------------------------
# Subtasks
# ---------------------------------------------------------------------------


def _subtask_paths(
    project_config: ProjectConfig, parent_task_key: str, subtask_id: str
) -> tuple[Path, Path]:
    stdir = subtask_dir(project_config, parent_task_key, subtask_id)
    return stdir, stdir / "task.json"


def _require_subtask_id(subtask_id: str) -> None:
    if not TASK_NUMBER_RE.fullmatch(subtask_id):
        raise TaskOpsError(
            "ARGS",
            f"subtask_id must be exactly four decimal digits, got {subtask_id!r}",
            field="subtask_id",
        )


def _require_parent(project_config: ProjectConfig, parent_task_key: str) -> Path:
    parent_tdir = task_dir(project_config, parent_task_key)
    if not parent_tdir.is_dir():
        raise TaskOpsError(
            "NOT-FOUND",
            f"parent task directory not found: {_relative(parent_tdir, project_config)}",
            field="parent_task_key",
            suggestion=f"create parent task first: arch task init {parent_task_key}",
            exit_code=EXIT_NOT_FOUND,
        )
    return parent_tdir


def subtask_init(
    project_config: ProjectConfig, parent_task_key: str, subtask_id: str
) -> dict[str, Any]:
    _require_subtask_id(subtask_id)
    tdir = _require_parent(project_config, parent_task_key)
    with _task_writer(project_config, tdir):
        pending = pending_write(tdir)
        if pending:
            raise TaskOpsError("CONFLICT", pending["message"], field="subtasks", exit_code=EXIT_CONFLICT)
        _assert_subtasks_directory(tdir)
        return _subtask_init(project_config, parent_task_key, subtask_id)


def _subtask_init(project_config: ProjectConfig, parent_task_key: str, subtask_id: str) -> dict[str, Any]:
    stdir, stjson = _subtask_paths(project_config, parent_task_key, subtask_id)
    if stdir.exists() or stdir.is_symlink():
        raise TaskOpsError(
            "CONFLICT",
            f"subtask directory already exists: {_relative(stdir, project_config)}",
            field="subtask_id",
            exit_code=EXIT_CONFLICT,
            suggestion=f"use a different --subtask-id or remove {_relative(stdir, project_config)}",
        )
    try:
        (stdir / "stage1").mkdir(parents=True, exist_ok=True)
        write_json_record(
            stjson, json.loads(scaffold_subtask_json(parent_task_key, subtask_id))
        )
    except OSError as exc:
        stjson.unlink(missing_ok=True)
        raise TaskOpsError(
            "WRITE",
            f"cannot write subtask record: {exc}",
            field="task.json",
            suggestion=f"check permissions for {_relative(stdir, project_config)}",
        ) from None
    return {
        "ok": True,
        "parent_task_key": parent_task_key,
        "subtask_id": subtask_id,
        "subtask_key": f"{parent_task_key}-{subtask_id}",
        "directory": _relative(stdir, project_config),
        "task_json": _relative(stjson, project_config),
        "stage_dir": _relative(stdir / "stage1", project_config),
        "note": "subtasks are always manual; no external source binding",
    }


def subtask_validate(
    project_config: ProjectConfig, parent_task_key: str, subtask_id: str
) -> tuple[str, list[str]]:
    _require_subtask_id(subtask_id)
    _require_parent(project_config, parent_task_key)
    stdir, stjson = _subtask_paths(project_config, parent_task_key, subtask_id)
    if not stjson.exists():
        raise TaskOpsError(
            "NOT-FOUND",
            f"subtask task.json not found: {_relative(stjson, project_config)}",
            field="subtask_id",
            exit_code=EXIT_NOT_FOUND,
            suggestion=f"create it: arch task subtask init {parent_task_key} {subtask_id}",
        )
    try:
        data = json.loads(stjson.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise TaskOpsError(
            "INVALID",
            f"subtask task.json invalid JSON: {exc}",
            field="task.json",
            suggestion=f"fix JSON syntax in {_relative(stjson, project_config)}",
        ) from None
    if not isinstance(data, dict):
        raise TaskOpsError(
            "INVALID",
            "subtask task.json must be a JSON object",
            field="task.json",
            suggestion=f"fix {_relative(stjson, project_config)}",
        )
    errors = validate_task_json(
        data, f"{parent_task_key}-{subtask_id}", project_config
    )
    if (stdir / "task.md").exists():
        errors.append(TASK_MD_ERROR)
    if not errors and data.get("acceptance_policy") == CASE_COVERAGE:
        _, errors = acceptance_state(project_config.root, stdir, data,
                                     current_stage(list_stages(stdir)), check_evidence=False)
    return f"subtask {parent_task_key}-{subtask_id} is valid", errors


def subtask_status(
    project_config: ProjectConfig, parent_task_key: str, subtask_id: str
) -> dict[str, Any]:
    _require_subtask_id(subtask_id)
    _require_parent(project_config, parent_task_key)
    stdir, stjson = _subtask_paths(project_config, parent_task_key, subtask_id)
    if not stjson.exists():
        raise TaskOpsError(
            "NOT-FOUND",
            f"subtask task.json not found: {_relative(stjson, project_config)}",
            field="subtask_id",
            exit_code=EXIT_NOT_FOUND,
        )
    try:
        data = json.loads(stjson.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise TaskOpsError(
            "INVALID",
            f"subtask task.json invalid JSON: {exc}",
            field="task.json",
        ) from None
    if not isinstance(data, dict):
        raise TaskOpsError(
            "INVALID",
            "subtask task.json must be a JSON object",
            field="task.json",
        )
    return {
        "parent_task_key": parent_task_key,
        "subtask_id": subtask_id,
        "subtask_key": f"{parent_task_key}-{subtask_id}",
        "directory": _relative(stdir, project_config),
        "task_json": _relative(stjson, project_config),
        "stages": list_stages(stdir),
        "sub_subtasks": list_sub_subtasks(stdir),
        "phase": data.get("phase", "unset"),
        "task_type": data.get("task_type", "unset"),
    }
