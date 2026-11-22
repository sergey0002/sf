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

from .acceptance import CASE_COVERAGE, acceptance_state, snapshot_problems
from .cli.errors import EXIT_CONFLICT, EXIT_ERROR, EXIT_NOT_FOUND
from .constants import TASK_KEY_RE, TASK_NUMBER_RE
from .flows import (
    FLOW_SCHEMA_VERSION,
    FlowError,
    find_transition,
    initial_flow_state,
    load_flow,
    select_flow as select_flow_rule,
    transition_options,
)
from .fs_atomic import (
    JournalError, WriterBusyError, clear_journal, journal_path, lock_directory,
    read_journal, stale_write_temps, write_journal, write_json_record,
)
from .identity import task_dir
from .project_config import ProjectConfig
from .schema import scaffold_task_json
from .store import ArchitectureStore
from . import task_record
from .subtask import (
    current_stage,
    list_stages,
    list_sub_subtasks,
    scaffold_subtask_json,
    subtask_dir,
)
from .validation import (
    inspect_subtasks,
    load_task_conf_types,
    validate_paths,
    validate_task_json,
)

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
    return _read_task_file(project_config, tjson, invalid_message)


def load_task_by_key(
    project_config: ProjectConfig,
    key: str,
    *,
    invalid_message: str = "cannot read task.json",
) -> dict[str, Any]:
    """Read a parent task or ``<parent>-<subtask_id>`` record."""
    _, tjson = task_or_subtask_paths(project_config, key)
    return _read_task_file(project_config, tjson, invalid_message)


def _read_task_file(
    project_config: ProjectConfig, tjson: Path, invalid_message: str
) -> dict[str, Any]:
    try:
        data = json.loads(tjson.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise TaskOpsError(
            "NOT-FOUND",
            f"task.json not found: {_relative(tjson, project_config)}",
            field="task_key",
            suggestion="create it: arch task init <task_key>",
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


def record_state(tdir: Path, task_key: str) -> dict[str, Any] | None:
    """Return a versioned state, or ``None`` for legacy records and read errors."""
    try:
        return task_record.read_state(tdir, task_key)
    except task_record.RecordError:
        return None


def effective_task(data: dict[str, Any], state: dict[str, Any] | None) -> dict[str, Any]:
    """Overlay the mutable phase from ``state.json`` onto a task record."""
    if state is not None and isinstance(state.get("phase"), str):
        return {**data, "phase": state["phase"]}
    return data


def load_effective_task(project_config: ProjectConfig, task_key: str) -> dict[str, Any]:
    tdir, _ = task_paths(project_config, task_key)
    return effective_task(load_task(project_config, task_key), record_state(tdir, task_key))


def record_info(tdir: Path, task_key: str) -> dict[str, Any] | None:
    """Summarize the versioned record, including stale or invalid journals."""
    if not (tdir / task_record.STATE_NAME).exists() and not (tdir / task_record.EVENTS_NAME).exists():
        return None
    try:
        state = task_record.read_state(tdir, task_key)
        events = task_record.read_events(tdir)
        computed = task_record.replay_state(task_key, events) if events else None
    except task_record.RecordError as exc:
        return {"state": "invalid", "message": exc.message}
    if state is None:
        return {"state": "missing", "event_count": len(events),
                "message": "state.json is missing; run task replay"}
    return {
        "state": "ok" if computed == state else "stale",
        "revision": state["revision"],
        "phase": state["phase"],
        "event_count": state["event_count"],
        "flow_version": state["flow_version"],
    }




def validation_errors(
    project_config: ProjectConfig, tdir: Path, data: dict[str, Any], task_key: str
) -> list[str]:
    errors = validate_task_json(data, task_key, project_config)
    errors.extend(task_record.record_errors(project_config, tdir, data, task_key))
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
    title: str | None = None,
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
        scaffold = json.loads(
            scaffold_task_json(task_key, task_number, source_type, source_prefix)
        )
        if title is not None:
            scaffold["title"] = title
        write_json_record(tjson, scaffold)
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
    state = record_state(tdir, task_key)
    data = effective_task(data, state)
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
    info = record_info(tdir, task_key)
    if info is not None:
        result["record"] = info
    pending = pending_write(tdir)
    if pending is not None:
        result["incomplete_write"] = pending
    return result


# ---------------------------------------------------------------------------
# Flow selection and transitions
# ---------------------------------------------------------------------------


def _flow_context(
    project_config: ProjectConfig, data: dict[str, Any], state: dict[str, Any] | None,
) -> tuple[dict[str, Any] | None, list[str], str | None]:
    type_id = data.get("task_type")
    flow_id = data.get("flow")
    if not isinstance(type_id, str) or not isinstance(flow_id, str):
        return None, ["task.json: task_type and flow are required for flow operations"], None
    flow, errors = load_flow(project_config, type_id, flow_id)
    current = state.get("flow_state") if state is not None else None
    if current is None:
        current = initial_flow_state(flow)
    return flow, errors, current


def flow_diagnosis(
    project_config: ProjectConfig, data: dict[str, Any], state: dict[str, Any] | None,
) -> dict[str, Any]:
    flow, errors, current = _flow_context(project_config, data, state)
    result: dict[str, Any] = {"state": current, "available_transitions": transition_options(flow, current)}
    if flow is not None:
        result.update(
            schema_version=flow.get("schema_version"),
            initial_state=flow.get("initial_state"),
            terminal_states=flow.get("terminal_states", []),
        )
        if current in flow.get("terminal_states", []):
            result["terminal"] = True
    if errors:
        result["errors"] = errors
    return result


def select_flow(
    project_config: ProjectConfig, type_id: str, facts: list[str],
) -> dict[str, Any]:
    try:
        return select_flow_rule(project_config, type_id, facts)
    except FlowError as exc:
        raise TaskOpsError(
            exc.code, exc.message, field=exc.field,
            suggestion=exc.suggestion, exit_code=exc.exit_code,
        ) from None


def advance(
    project_config: ProjectConfig,
    task_key: str,
    event: str,
    expected_revision: int,
    *,
    dry_run: bool,
    event_id: str | None = None,
) -> dict[str, Any]:
    tdir, tjson = task_paths(project_config, task_key)
    data = load_task(project_config, task_key)
    state = record_state(tdir, task_key)
    if state is None:
        raise TaskOpsError(
            "RECORD", "task record is not versioned", field="record_version",
            suggestion=f"run `arch task migrate {task_key}` first",
        )
    flow, errors, current = _flow_context(project_config, data, state)
    if errors:
        raise TaskOpsError(
            "CONFIG", "; ".join(errors), field="flow",
            suggestion=f"fix flow {data.get('task_type')}/{data.get('flow')}",
        )
    if not isinstance(flow, dict) or flow.get("schema_version") != FLOW_SCHEMA_VERSION:
        raise TaskOpsError(
            "UNSUPPORTED-FLOW",
            f"flow {data.get('task_type')}/{data.get('flow')} is not a versioned "
            f"{FLOW_SCHEMA_VERSION} definition",
            field="flow",
            suggestion="add schema_version: flow-1 with initial_state, states and transitions",
        )
    if current is None:
        raise TaskOpsError(
            "NO-FLOW", "the selected flow has no initial state", field="flow",
            suggestion="declare initial_state in the flow YAML",
        )
    event_id = event_id or f"flow:{task_key}:{state['revision']}:{event}"
    try:
        existing_events = task_record.read_events(tdir)
    except task_record.RecordError as exc:
        raise TaskOpsError(exc.code, exc.message, field=exc.field,
                           suggestion=exc.suggestion, exit_code=exc.exit_code) from None
    existing = next((item for item in existing_events if item["event_id"] == event_id), None)
    if existing is not None:
        payload = existing.get("payload", {})
        if (existing.get("type") == task_record.FLOW_TRANSITIONED
                and existing.get("expected_revision") == expected_revision
                and payload.get("event") == event):
            transition_id = str(payload.get("transition_id"))
            current = str(payload.get("from"))
            target = str(payload.get("to"))
        else:
            raise TaskOpsError(
                "CONFLICT", f"event {event_id!r} already exists with different content",
                field="event_id", exit_code=EXIT_CONFLICT,
                suggestion="use a new --id for a different transition",
            )
    else:
        try:
            transition = find_transition(flow, current, event)
        except FlowError as exc:
            raise TaskOpsError(
                exc.code, exc.message, field=exc.field,
                suggestion=exc.suggestion, exit_code=exc.exit_code,
            ) from None
        transition_id = str(transition.get("id"))
        target = str(transition.get("to"))
    try:
        with _task_writer(project_config, tdir):
            payload = task_record.append_flow_transition(
                project_config, tdir, data, event_id=event_id,
                expected_revision=expected_revision, source=current,
                event=event, target=target, transition_id=transition_id,
                dry_run=dry_run,
            )
    except task_record.RecordError as exc:
        raise TaskOpsError(exc.code, exc.message, field=exc.field,
                           suggestion=exc.suggestion, exit_code=exc.exit_code) from None
    if dry_run:
        updated = effective_task(data, {**state, "flow_state": target})
    else:
        updated = effective_task(data, record_state(tdir, task_key))
    summary = diagnose(
        project_config, task_key, str(data.get("task_number", "")),
        str((data.get("source") or {}).get("type", "ui")), True,
    )
    summary.update({
        "transition": {
            "id": transition_id, "event": event, "from": current, "to": target,
        },
        "record": payload,
        "flow_info": flow_diagnosis(project_config, updated, record_state(tdir, task_key) if not dry_run else {
            **state, "flow_state": target,
        }),
    })
    return summary


# ---------------------------------------------------------------------------
# Composite write: decompose
# ---------------------------------------------------------------------------


def _dependency_specs(values: list[str]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for value in values:
        subtask_id, separator, raw = value.partition("=")
        if not separator or not TASK_NUMBER_RE.fullmatch(subtask_id.strip()):
            raise TaskOpsError(
                "ARGS", f"--subtask-depends-on must use ID=DEP[,DEP], got {value!r}",
                field="subtask_depends_on",
                suggestion="example: --subtask-depends-on 0002=0001",
            )
        dependencies = [item.strip() for item in raw.split(",") if item.strip()]
        if not dependencies or any(not TASK_NUMBER_RE.fullmatch(dep) for dep in dependencies):
            raise TaskOpsError(
                "ARGS", f"--subtask-depends-on must name four-digit subtask ids, got {value!r}",
                field="subtask_depends_on",
            )
        subtask_id = subtask_id.strip()
        result.setdefault(subtask_id, [])
        result[subtask_id].extend(dep for dep in dependencies if dep not in result[subtask_id])
    return result


def _shape_specs(values: list[str], flag: str) -> dict[str, str]:
    """Parse repeatable ID=VALUE flags used to choose a subtask's shape."""
    result: dict[str, str] = {}
    for value in values or []:
        subtask_id, separator, raw = value.partition("=")
        if not separator or not TASK_NUMBER_RE.fullmatch(subtask_id.strip()) or not raw.strip():
            raise TaskOpsError(
                "ARGS", f"{flag} must use ID=VALUE, got {value!r}",
                field=flag,
                suggestion="example: --subtask-type 0001=feature",
            )
        result[subtask_id.strip()] = raw.strip()
    return result


def _estimate_value(value: str, flag: str) -> int | float:
    try:
        hours = float(value)
    except (TypeError, ValueError):
        raise TaskOpsError(
            "ARGS", f"{flag} must be a number of hours, got {value!r}", field=flag,
        ) from None
    if hours <= 0:
        raise TaskOpsError(
            "ARGS", f"{flag} must be positive, got {value!r}", field=flag,
        )
    return int(hours) if hours.is_integer() else hours


def _planned_subtasks(
    task_key: str,
    subtask_ids: list[str],
    subtask_titles: list[str],
    dependency_specs: list[str] | None = None,
    type_specs: list[str] | None = None,
    flow_specs: list[str] | None = None,
    complexity_specs: list[str] | None = None,
    estimate_specs: list[str] | None = None,
) -> list[dict[str, Any]]:
    if len(subtask_ids) != len(subtask_titles):
        raise TaskOpsError(
            "ARGS",
            "--subtask-id and --subtask-title must be provided in equal numbers",
            field="subtask",
            suggestion="provide the same number of --subtask-id and --subtask-title flags",
        )
    dependencies = _dependency_specs(dependency_specs or [])
    types = _shape_specs(type_specs or [], "--subtask-type")
    flows = _shape_specs(flow_specs or [], "--subtask-flow")
    complexities = _shape_specs(complexity_specs or [], "--subtask-complexity")
    estimates = _shape_specs(estimate_specs or [], "--subtask-estimate")
    planned: list[dict[str, Any]] = []
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
        entry: dict[str, Any] = {"id": subtask_id, "title": title}
        if dependencies.get(subtask_id):
            entry["depends_on"] = dependencies[subtask_id]
        if types.get(subtask_id):
            entry["task_type"] = types[subtask_id]
        if flows.get(subtask_id):
            entry["flow"] = flows[subtask_id]
        if complexities.get(subtask_id):
            entry["complexity"] = complexities[subtask_id]
        if estimates.get(subtask_id):
            entry["estimate_hours"] = _estimate_value(
                estimates[subtask_id], f"--subtask-estimate {subtask_id}"
            )
        planned.append(entry)
    unknown = sorted(
        (set(dependencies) | set(types) | set(flows) | set(complexities) | set(estimates))
        - seen
    )
    if unknown:
        raise TaskOpsError(
            "ARGS", f"shape or dependency declared for unknown subtask(s): {', '.join(unknown)}",
            field="subtask_depends_on",
            suggestion="declare the subtask with --subtask-id before adding its shape or dependencies",
        )
    return planned


def _journal_package_matches(recorded: Any, planned: list[dict[str, Any]]) -> bool:
    """Accept an older journal that recorded only ids, titles and dependencies."""
    if not isinstance(recorded, list) or len(recorded) != len(planned):
        return False
    keys = ("depends_on", "task_type", "flow", "complexity", "estimate_hours")
    for saved, current in zip(recorded, planned):
        if not isinstance(saved, dict):
            return False
        if saved.get("id") != current.get("id") or saved.get("title") != current.get("title"):
            return False
        for key in keys:
            if key in saved and saved.get(key) != current.get(key):
                return False
    return True


def _validate_subtask_shapes(
    project_config: ProjectConfig, planned: list[dict[str, Any]]
) -> None:
    """Reject a child shape that the task-conf does not allow."""
    if not any(entry.get("task_type") for entry in planned):
        return
    types, errors = load_task_conf_types(project_config)
    if errors:
        raise TaskOpsError("CONFIG", "; ".join(errors), field="task_type")
    for entry in planned:
        task_type = entry.get("task_type")
        if task_type is None:
            continue
        conf = types.get(task_type)
        if conf is None:
            raise TaskOpsError(
                "ARGS", f"subtask {entry['id']}: unknown task_type {task_type!r}",
                field="task_type",
                suggestion=f"use one of: {', '.join(sorted(types))}",
            )
        flow = entry.get("flow")
        if flow is not None:
            allowed_flows = conf.get("allowed_flows", [])
            if flow not in allowed_flows:
                raise TaskOpsError(
                    "ARGS",
                    f"subtask {entry['id']}: flow {flow!r} not allowed for task_type {task_type!r}; "
                    f"allowed: {', '.join(allowed_flows) or 'none'}",
                    field="flow",
                )
        complexity = entry.get("complexity")
        if complexity is not None:
            allowed_complexity = conf.get("complexity_allowed", [])
            if allowed_complexity and complexity not in allowed_complexity:
                raise TaskOpsError(
                    "ARGS",
                    f"subtask {entry['id']}: complexity must be one of "
                    f"{'/'.join(allowed_complexity)}, got {complexity!r}",
                    field="complexity",
                )


def _check_package_collisions(
    project_config: ProjectConfig,
    tdir: Path,
    task_key: str,
    data: dict[str, Any],
    planned: list[dict[str, Any]],
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


def _validate_dependency_graph(
    declared: list[dict[str, Any]], planned: list[dict[str, Any]]
) -> None:
    graph: dict[str, list[str]] = {}
    for record in declared:
        if isinstance(record, dict) and isinstance(record.get("id"), str):
            deps = record.get("depends_on", [])
            graph[record["id"]] = deps if isinstance(deps, list) else []
    for entry in planned:
        graph[entry["id"]] = entry.get("depends_on", [])
    known = set(graph)
    for subtask_id, dependencies in graph.items():
        for dep in dependencies:
            if dep not in known:
                raise TaskOpsError(
                    "VALIDATION", f"subtask {subtask_id} depends on unknown subtask {dep}",
                    field="subtask_depends_on",
                    suggestion="add the dependency to the package or remove it",
                )
    visiting: list[str] = []
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            cycle = visiting[visiting.index(node):] + [node]
            raise TaskOpsError(
                "CONFLICT", f"subtask dependency cycle: {' -> '.join(cycle)}",
                field="subtask_depends_on", exit_code=EXIT_CONFLICT,
                suggestion="remove the circular dependency before writing the package",
            )
        visiting.append(node)
        for dep in graph.get(node, []):
            visit(dep)
        visiting.pop()
        visited.add(node)

    for subtask_id in graph:
        visit(subtask_id)


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
    subtask_depends_on: list[str] | None = None,
    subtask_types: list[str] | None = None,
    subtask_flows: list[str] | None = None,
    subtask_complexities: list[str] | None = None,
    subtask_estimates: list[str] | None = None,
) -> dict[str, Any]:
    """Serialize writes to the parent and validate the whole package before writing."""
    tdir, tjson = task_paths(project_config, task_key)
    if not tdir.is_dir():
        load_task(project_config, task_key)  # Preserve the public not-found result.
    with _task_writer(project_config, tdir):
        return _decompose_locked(
            project_config, task_key, tdir, tjson, subtask_ids, subtask_titles,
            subtask_depends_on or [], subtask_types or [], subtask_flows or [],
            subtask_complexities or [], subtask_estimates or [],
        )


def _decompose_locked(
    project_config: ProjectConfig, task_key: str, tdir: Path, tjson: Path,
    subtask_ids: list[str], subtask_titles: list[str],
    subtask_depends_on: list[str],
    subtask_types: list[str],
    subtask_flows: list[str],
    subtask_complexities: list[str],
    subtask_estimates: list[str],
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

    planned = _planned_subtasks(
        task_key, subtask_ids, subtask_titles, subtask_depends_on,
        subtask_types, subtask_flows, subtask_complexities, subtask_estimates,
    )
    default_complexity = data.get("complexity") or "low"
    for entry in planned:
        if "task_type" not in entry:
            entry["task_type"] = "subtask"
            entry.setdefault("flow", None)
        entry.setdefault("complexity", default_complexity)
    _validate_subtask_shapes(project_config, planned)
    declared_records = data.get("subtasks", [])
    _validate_dependency_graph(declared_records, planned)
    journal_file = journal_path(tdir)
    try:
        journal = read_journal(tdir)
    except JournalError as exc:
        raise TaskOpsError(
            "CONFLICT", f"Invalid write journal {journal_file.name}: {exc}", field="subtasks",
            exit_code=EXIT_CONFLICT, suggestion="inspect the journal and records before retrying",
        ) from exc
    if journal is not None and not _journal_package_matches(journal["subtasks"], planned):
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
            record = {"id": subtask_id, "title": title, "status": "open", "path": path}
            if entry.get("depends_on"):
                record["depends_on"] = entry["depends_on"]
            for key, value in (
                ("task_type", entry.get("task_type")),
                ("flow", entry.get("flow")),
                ("complexity", entry.get("complexity")),
                ("estimate_hours", entry.get("estimate_hours")),
            ):
                if value is not None:
                    record[key] = value
            new_records.append(record)
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
                child = json.loads(scaffold_subtask_json(
                    task_key, entry["id"], entry["title"],
                    task_type=entry.get("task_type"),
                    flow=entry.get("flow"),
                    complexity=entry.get("complexity"),
                    estimate_hours=entry.get("estimate_hours"),
                ))
                child["depends_on"] = [
                    f"{task_key}-{dep}" for dep in entry.get("depends_on", [])
                ]
                write_json_record(stjson, child)
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
                dep_state = record_state(path.parent, key)
                dep = effective_task(dep, dep_state)
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


def _requires_docs_gate(task: dict[str, Any]) -> bool:
    return (task.get("task_type") == "docs" and task.get("flow") == "docs-only"
            and task.get("acceptance_policy") == CASE_COVERAGE)


def _evidence_blockers(root: Path, tdir: Path, stage: str | None) -> list[str]:
    """Block closure when a declared evidence snapshot no longer matches.

    Tasks without ``case-coverage-v1`` may omit evidence. When they do record
    ``snapshot_files``, a stale snapshot is treated as an unverified result.
    """
    if stage is None:
        return []
    path = tdir / stage / "verification.json"
    try:
        evidence = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return []
    except (OSError, ValueError) as exc:
        return [f"evidence {stage}: cannot read verification.json: {exc}"]
    if not isinstance(evidence, dict) or not evidence.get("snapshot_files"):
        return []
    problems = snapshot_problems(root, evidence.get("snapshot_files"), path.parent / "plan.md")
    return [f"evidence {stage}: {problem}" for problem in problems]


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
    else:
        blockers.extend(_evidence_blockers(project_config.root, tdir, stage))
    pending = pending_write(tdir)
    if pending is not None:
        blockers = [pending["message"]] + blockers
    if not blockers and _requires_docs_gate(data):
        # Evidence is editable; re-run the fixed structural checks, not commands from it.
        blockers.extend(f"docs-only validate: {error}"
                        for error in ArchitectureStore(project_config).validate(check_index=True))
        blockers.extend(f"docs-only paths-check: {error}" for error in validate_paths(project_config))
    return children, subtask_errors, blockers, pending, plan_ready, dependencies


def diagnose(
    project_config: ProjectConfig, task_key: str, task_number: str, source_type: str, brief: bool
) -> dict[str, Any]:
    tdir, tjson = task_paths(project_config, task_key)
    data = load_task(project_config, task_key)
    state = record_state(tdir, task_key)
    data = effective_task(data, state)
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
    info = record_info(tdir, task_key)
    if info is not None:
        result["record"] = info
    if pending is not None:
        result["incomplete_write"] = pending
    if plan_ready is not None:
        result["acceptance_plan_ready"] = plan_ready
    flow = flow_diagnosis(project_config, data, state)
    result["flow_state"] = flow.get("state")
    result["available_transitions"] = flow.get("available_transitions", [])
    result["flow_schema_version"] = flow.get("schema_version")
    if flow.get("terminal"):
        result["flow_terminal"] = True
    if flow.get("errors"):
        result["flow_errors"] = flow["errors"]
    result["subtasks_ready"] = sum(row.get("ready") and row.get("phase") != "completed"
                                   for row in subtasks)
    result["subtasks_blocked"] = sum(row.get("readiness") == "blocked" for row in subtasks)
    result["subtasks_completed"] = sum(row.get("phase") == "completed" for row in subtasks)
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


def _sync_closed_records(tjson: Path, tdir: Path, data: dict[str, Any]) -> bool:
    """Mark completed children and the current stage in the parent card.

    ``subtasks`` and ``stage_history`` are mutable fields, so this keeps the
    card consistent with the children without touching immutable intent.
    """
    changed = False
    subtasks = data.get("subtasks")
    if isinstance(subtasks, list):
        for entry in subtasks:
            if not isinstance(entry, dict) or entry.get("status") == "completed":
                continue
            sub_id = entry.get("id")
            if not isinstance(sub_id, str):
                continue
            try:
                child = json.loads((tdir / "subtasks" / sub_id / "task.json").read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if isinstance(child, dict) and child.get("phase") == "completed":
                entry["status"] = "completed"
                changed = True

    stage = current_stage(list_stages(tdir))
    if stage is not None:
        history = data.get("stage_history")
        if not isinstance(history, list):
            history = []
            data["stage_history"] = history
            changed = True
        match = next(
            (item for item in history
             if isinstance(item, dict) and item.get("stage_id") == stage),
            None,
        )
        if match is None:
            history.append({"stage_id": stage, "status": "completed"})
            changed = True
        elif match.get("status") != "completed":
            match["status"] = "completed"
            changed = True

    if changed:
        write_json_record(tjson, data)
    return changed


def close(
    project_config: ProjectConfig, task_key: str, dry_run: bool
) -> tuple[dict[str, Any], list[str]]:
    tdir, tjson = task_or_subtask_paths(project_config, task_key)
    if dry_run or not tdir.is_dir():
        return _close_task(project_config, task_key, tdir, tjson, dry_run)
    with _task_writer(project_config, tdir):
        return _close_task(project_config, task_key, tdir, tjson, dry_run)


def _close_task(project_config: ProjectConfig, task_key: str, tdir: Path, tjson: Path,
                dry_run: bool) -> tuple[dict[str, Any], list[str]]:
    data = load_task_by_key(project_config, task_key)
    state = record_state(tdir, task_key)
    effective = effective_task(data, state)
    _, _, blockers, _, _, _ = closure_state(
        project_config, tdir, task_key, effective, current_stage(list_stages(tdir))
    )
    if dry_run:
        return {"would_close": not blockers, "task_key": task_key, "blockers": blockers}, blockers
    if blockers:
        return {}, blockers
    if state is not None:
        if effective.get("phase") == "completed":
            return {"ok": True, "task_key": task_key, "phase": "completed",
                    "already_closed": True}, []
        _sync_closed_records(tjson, tdir, data)
        try:
            payload = task_record.append_event(
                project_config, tdir, data,
                event_id=f"close:{task_key}", event_type=task_record.PHASE_CHANGED,
                expected_revision=state["revision"], phase="completed", summary=None,
                dry_run=False,
            )
        except task_record.RecordError as exc:
            raise TaskOpsError(
                exc.code, exc.message, field=exc.field,
                suggestion=exc.suggestion, exit_code=exc.exit_code,
            ) from None
        return {"ok": True, "task_key": task_key, "phase": "completed",
                "revision": payload["revision"]}, []
    _sync_closed_records(tjson, tdir, data)
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
# Versioned record operations
# ---------------------------------------------------------------------------


def _record_task(project_config: ProjectConfig, key: str) -> tuple[Path, dict[str, Any]]:
    tdir, tjson = task_or_subtask_paths(project_config, key)
    if not tjson.exists():
        raise TaskOpsError(
            "NOT-FOUND",
            f"task.json not found: {_relative(tjson, project_config)}",
            field="task_key",
            suggestion=f"create it: arch task init {key}",
            exit_code=EXIT_NOT_FOUND,
        )
    return tdir, load_task_by_key(project_config, key)


def migrate_record(project_config: ProjectConfig, key: str, dry_run: bool) -> dict[str, Any]:
    tdir, data = _record_task(project_config, key)
    if dry_run:
        return task_record.migrate(project_config, tdir, data, dry_run=True)
    with _task_writer(project_config, tdir):
        return task_record.migrate(project_config, tdir, data, dry_run=False)


def append_record_event(
    project_config: ProjectConfig,
    key: str,
    *,
    event_id: str,
    event_type: str,
    expected_revision: int,
    phase: str | None,
    summary: str | None,
    dry_run: bool,
) -> dict[str, Any]:
    tdir, data = _record_task(project_config, key)
    if (event_type == task_record.PHASE_CHANGED and phase == "completed"
            and tdir.parent == project_config.tasks_root and _requires_docs_gate(data)):
        raise TaskOpsError("VALIDATION", "complete this docs-only task via arch task close", field="phase")
    if dry_run:
        return task_record.append_event(
            project_config, tdir, data, event_id=event_id, event_type=event_type,
            expected_revision=expected_revision, phase=phase, summary=summary, dry_run=True,
        )
    with _task_writer(project_config, tdir):
        return task_record.append_event(
            project_config, tdir, data, event_id=event_id, event_type=event_type,
            expected_revision=expected_revision, phase=phase, summary=summary, dry_run=False,
        )


def replay_record(project_config: ProjectConfig, key: str, dry_run: bool) -> dict[str, Any]:
    tdir, data = _record_task(project_config, key)
    if dry_run:
        return task_record.replay(project_config, tdir, data, dry_run=True)
    with _task_writer(project_config, tdir):
        return task_record.replay(project_config, tdir, data, dry_run=False)


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
    project_config: ProjectConfig,
    parent_task_key: str,
    subtask_id: str,
    *,
    task_type: str | None = None,
    flow: str | None = None,
    complexity: str | None = None,
    estimate_hours: float | None = None,
) -> dict[str, Any]:
    _require_subtask_id(subtask_id)
    tdir = _require_parent(project_config, parent_task_key)
    parent = load_task(project_config, parent_task_key)
    shape = {
        "task_type": task_type or "subtask",
        "flow": flow,
        "complexity": complexity or parent.get("complexity") or "low",
        "estimate_hours": estimate_hours,
    }
    with _task_writer(project_config, tdir):
        pending = pending_write(tdir)
        if pending:
            raise TaskOpsError("CONFLICT", pending["message"], field="subtasks", exit_code=EXIT_CONFLICT)
        _assert_subtasks_directory(tdir)
        return _subtask_init(project_config, parent_task_key, subtask_id, shape)


def _subtask_init(
    project_config: ProjectConfig,
    parent_task_key: str,
    subtask_id: str,
    shape: dict[str, Any],
) -> dict[str, Any]:
    _validate_subtask_shapes(project_config, [{"id": subtask_id, **shape}])
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
            stjson,
            json.loads(scaffold_subtask_json(
                parent_task_key, subtask_id,
                task_type=shape.get("task_type"),
                flow=shape.get("flow"),
                complexity=shape.get("complexity"),
                estimate_hours=shape.get("estimate_hours"),
            )),
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
    errors.extend(task_record.record_errors(
        project_config, stdir, data, f"{parent_task_key}-{subtask_id}"
    ))
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
    data = effective_task(data, record_state(stdir, f"{parent_task_key}-{subtask_id}"))
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
