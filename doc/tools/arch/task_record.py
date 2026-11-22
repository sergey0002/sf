"""Versioned task record: immutable intent, mutable state and event journal.

Legacy records have no ``record_version`` and keep ``phase`` in ``task.json``.
They are read unchanged. :func:`migrate` adds ``record_version``,
``flow_version`` and ``intent_digest`` to ``task.json`` without touching intent
fields, then creates ``state.json`` and an append-only ``events.jsonl``.

Every event carries a monotonic ``revision``, the ``expected_revision`` it was
applied to, an ``event_id`` idempotency key and a ``prev_digest`` chain link.
:func:`replay_state` folds the journal into a state and is the recovery path
after an interrupted write: a journal that does not verify is never
materialized as a successful state.
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
from pathlib import Path
from typing import Any

from .cli.errors import EXIT_CONFLICT, EXIT_ERROR
from .flows import initial_flow_state, load_flow
from .fs_atomic import atomic_write_text, write_json_record
from .project_config import ProjectConfig

RECORD_VERSION = 1
STATE_SCHEMA = "task-state-1"
STATE_NAME = "state.json"
EVENTS_NAME = "events.jsonl"

MIGRATED = "record.migrated"
PHASE_CHANGED = "phase.changed"
RESULT_RECORDED = "result.recorded"
FLOW_TRANSITIONED = "flow.transitioned"
EVENT_TYPES = (MIGRATED, PHASE_CHANGED, RESULT_RECORDED, FLOW_TRANSITIONED)

EVENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")

# Immutable intent: lifecycle writes never change these values. ``phase``,
# ``subtasks``, ``stage_history`` and ``changed_files`` stay mutable.
INTENT_FIELDS = (
    "title", "kind", "intent", "source", "scope", "acceptance_criteria",
    "contracts_and_invariants", "project_context_refs", "constraints",
    "assumptions", "open_questions", "risk", "authority", "approvals",
    "task_type", "flow", "complexity", "estimate_hours", "target_release", "rollback_plan",
    "implementation_plan", "evidence", "depends_on", "related_docs",
    "related_tests", "research_docs", "owner", "priority",
)

RECORD_FIELDS = ("record_version", "flow_version", "intent_digest")


class RecordError(ValueError):
    """A deterministic task-record failure rendered as a CLI envelope."""

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


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def intent_payload(task: dict[str, Any]) -> dict[str, Any]:
    """Return only the immutable intent subset, including absent values."""
    return {field: task.get(field) for field in INTENT_FIELDS}


def intent_digest(task: dict[str, Any]) -> str:
    return _digest({"intent_version": 1, "fields": intent_payload(task)})


def flow_version(config: ProjectConfig, task: dict[str, Any]) -> str | None:
    """Pin the flow template by content, not by a mutable name alone."""
    task_type = task.get("task_type")
    flow = task.get("flow")
    if not isinstance(task_type, str) or not isinstance(flow, str):
        return None
    path = config.task_conf_root / "types" / task_type / "flows" / flow / "config.yaml"
    try:
        payload = path.read_bytes()
    except OSError:
        return None
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def state_path(directory: Path) -> Path:
    return directory / STATE_NAME


def events_path(directory: Path) -> Path:
    return directory / EVENTS_NAME


def _reject_unsafe(path: Path, label: str) -> None:
    if path.is_symlink():
        raise RecordError("RECORD", f"{label} is a symbolic link", field=label)
    if path.exists() and not stat.S_ISREG(path.stat().st_mode):
        raise RecordError("RECORD", f"{label} is not a regular file", field=label)


def _state_body(state: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in state.items() if key != "state_digest"}


def build_state(
    task_key: str,
    *,
    flow_version_value: str | None,
    intent_digest_value: str,
    revision: int,
    phase: str | None,
    event_count: int,
    last_event_id: str | None,
    flow_state: str | None = None,
) -> dict[str, Any]:
    body = {
        "schema_version": STATE_SCHEMA,
        "task_key": task_key,
        "record_version": RECORD_VERSION,
        "flow_version": flow_version_value,
        "intent_digest": intent_digest_value,
        "revision": revision,
        "phase": phase,
        "event_count": event_count,
        "last_event_id": last_event_id,
    }
    if flow_state is not None:
        body["flow_state"] = flow_state
    return {**body, "state_digest": _digest(body)}


def read_state(directory: Path, task_key: str | None = None) -> dict[str, Any] | None:
    """Return a validated state, ``None`` when absent, or raise RecordError."""
    path = state_path(directory)
    try:
        _reject_unsafe(path, STATE_NAME)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
    except RecordError:
        raise
    except (OSError, ValueError) as exc:
        raise RecordError("RECORD", f"cannot read {STATE_NAME}: {exc}", field=STATE_NAME) from None
    if not isinstance(data, dict):
        raise RecordError("RECORD", f"{STATE_NAME} must be a JSON object", field=STATE_NAME)
    if data.get("schema_version") != STATE_SCHEMA:
        raise RecordError("RECORD", f"{STATE_NAME}: unsupported schema_version", field=STATE_NAME)
    if data.get("record_version") != RECORD_VERSION:
        raise RecordError("RECORD", f"{STATE_NAME}: unsupported record_version", field=STATE_NAME)
    if task_key is not None and data.get("task_key") != task_key:
        raise RecordError("RECORD", f"{STATE_NAME}: task_key does not match {task_key}", field=STATE_NAME)
    revision = data.get("revision")
    if type(revision) is not int or revision < 1:
        raise RecordError("RECORD", f"{STATE_NAME}: revision must be a positive integer", field=STATE_NAME)
    if not isinstance(data.get("phase"), (str, type(None))):
        raise RecordError("RECORD", f"{STATE_NAME}: phase must be a string or null", field=STATE_NAME)
    if "flow_state" in data and not isinstance(data["flow_state"], (str, type(None))):
        raise RecordError("RECORD", f"{STATE_NAME}: flow_state must be a string or null", field=STATE_NAME)
    if type(data.get("event_count")) is not int or data["event_count"] < 1:
        raise RecordError("RECORD", f"{STATE_NAME}: event_count must be a positive integer", field=STATE_NAME)
    if data.get("state_digest") != _digest(_state_body(data)):
        raise RecordError("RECORD", f"{STATE_NAME}: state_digest does not match content", field=STATE_NAME)
    return data


def _validate_event(event: Any, index: int) -> dict[str, Any]:
    label = f"{EVENTS_NAME} line {index}"
    if not isinstance(event, dict):
        raise RecordError("EVENT", f"{label}: event must be an object", field=EVENTS_NAME)
    event_id = event.get("event_id")
    if not isinstance(event_id, str) or not EVENT_ID_RE.fullmatch(event_id):
        raise RecordError("EVENT", f"{label}: invalid event_id", field=EVENTS_NAME)
    if event.get("type") not in EVENT_TYPES:
        raise RecordError("EVENT", f"{label}: unknown event type", field=EVENTS_NAME)
    expected = event.get("expected_revision")
    revision = event.get("revision")
    if type(expected) is not int or expected < 0:
        raise RecordError("EVENT", f"{label}: invalid expected_revision", field=EVENTS_NAME)
    if type(revision) is not int or revision != expected + 1:
        raise RecordError("EVENT", f"{label}: revision must follow expected_revision", field=EVENTS_NAME)
    if not isinstance(event.get("payload"), dict):
        raise RecordError("EVENT", f"{label}: payload must be an object", field=EVENTS_NAME)
    prev = event.get("prev_digest")
    if prev is not None and not isinstance(prev, str):
        raise RecordError("EVENT", f"{label}: invalid prev_digest", field=EVENTS_NAME)
    digest = event.get("digest")
    if not isinstance(digest, str):
        raise RecordError("EVENT", f"{label}: missing digest", field=EVENTS_NAME)
    body = {key: value for key, value in event.items() if key != "digest"}
    if digest != _digest(body):
        raise RecordError("EVENT", f"{label}: digest does not match content", field=EVENTS_NAME)
    return event


def read_events(directory: Path) -> list[dict[str, Any]]:
    """Return a validated event journal; an absent journal is an empty list."""
    path = events_path(directory)
    try:
        _reject_unsafe(path, EVENTS_NAME)
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8")
    except RecordError:
        raise
    except (OSError, UnicodeError) as exc:
        raise RecordError("EVENT", f"cannot read {EVENTS_NAME}: {exc}", field=EVENTS_NAME) from None
    if text and not text.endswith("\n"):
        raise RecordError("EVENT", f"{EVENTS_NAME}: partial trailing line", field=EVENTS_NAME)
    events = []
    for number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError as exc:
            raise RecordError("EVENT", f"{EVENTS_NAME} line {number}: {exc}", field=EVENTS_NAME) from None
        events.append(_validate_event(event, number))
    return events


def replay_state(task_key: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    """Fold the journal into a state, rejecting broken chains and intent rewrites."""
    revision = 0
    phase: str | None = None
    flow_state: str | None = None
    flow_value: str | None = None
    intent_value: str | None = None
    prev_digest: str | None = None
    last_event_id: str | None = None
    for index, event in enumerate(events, start=1):
        _validate_event(event, index)
        if event["expected_revision"] != revision:
            raise RecordError(
                "EVENT",
                f"{EVENTS_NAME} line {index}: expected_revision {event['expected_revision']} "
                f"does not follow revision {revision}",
                field=EVENTS_NAME,
            )
        if event["prev_digest"] != prev_digest:
            raise RecordError(
                "EVENT",
                f"{EVENTS_NAME} line {index}: broken prev_digest chain",
                field=EVENTS_NAME,
            )
        payload = event["payload"]
        if event["type"] == MIGRATED:
            if index != 1:
                raise RecordError("EVENT", f"{MIGRATED} must be the first event", field=EVENTS_NAME)
            if "intent_digest" in payload:
                intent_value = payload.get("intent_digest")
            if "flow_version" in payload:
                flow_value = payload.get("flow_version")
            if "phase" in payload:
                phase = payload.get("phase")
            if "flow_state" in payload:
                flow_state = payload.get("flow_state")
        else:
            if "intent_digest" in payload or "flow_version" in payload:
                raise RecordError(
                    "EVENT",
                    f"{EVENTS_NAME} line {index}: lifecycle events cannot change intent or flow version",
                    field=EVENTS_NAME,
                )
            if event["type"] == PHASE_CHANGED:
                new_phase = payload.get("phase")
                if not isinstance(new_phase, str):
                    raise RecordError("EVENT", f"{EVENTS_NAME} line {index}: phase.changed requires a phase",
                                      field=EVENTS_NAME)
                phase = new_phase
            elif event["type"] == FLOW_TRANSITIONED:
                source = payload.get("from")
                target = payload.get("to")
                transition_id = payload.get("transition_id")
                event_name = payload.get("event")
                if (not isinstance(source, str) or not source
                        or not isinstance(target, str) or not target
                        or not isinstance(transition_id, str) or not transition_id
                        or not isinstance(event_name, str) or not event_name):
                    raise RecordError(
                        "EVENT",
                        f"{EVENTS_NAME} line {index}: flow.transitioned requires from, to, event and transition_id",
                        field=EVENTS_NAME,
                    )
                if flow_state is not None and source != flow_state:
                    raise RecordError(
                        "EVENT",
                        f"{EVENTS_NAME} line {index}: flow.transitioned from {source!r} does not follow {flow_state!r}",
                        field=EVENTS_NAME,
                    )
                flow_state = target
        revision = event["revision"]
        prev_digest = event["digest"]
        last_event_id = event["event_id"]
    if revision == 0:
        raise RecordError("EVENT", f"{EVENTS_NAME}: journal is empty", field=EVENTS_NAME)
    if not isinstance(intent_value, str):
        raise RecordError("EVENT", f"{EVENTS_NAME}: first event must pin intent_digest", field=EVENTS_NAME)
    return build_state(
        task_key,
        flow_version_value=flow_value,
        intent_digest_value=intent_value,
        revision=revision,
        phase=phase,
        event_count=len(events),
        last_event_id=last_event_id,
        flow_state=flow_state,
    )


def _write_events(directory: Path, events: list[dict[str, Any]]) -> None:
    atomic_write_text(events_path(directory), "".join(_canonical(event) + "\n" for event in events))


def _make_event(
    event_id: str,
    event_type: str,
    expected_revision: int,
    payload: dict[str, Any],
    prev_digest: str | None,
) -> dict[str, Any]:
    body = {
        "event_id": event_id,
        "type": event_type,
        "expected_revision": expected_revision,
        "revision": expected_revision + 1,
        "payload": payload,
        "prev_digest": prev_digest,
    }
    return {**body, "digest": _digest(body)}


def _migrate_event(task_key: str, task: dict[str, Any], config: ProjectConfig) -> dict[str, Any]:
    flow, _ = load_flow(config, task.get("task_type", ""), task.get("flow", ""))
    payload = {
        "phase": task.get("phase"),
        "flow_version": flow_version(config, task),
        "intent_digest": intent_digest(task),
        "flow_state": initial_flow_state(flow),
    }
    return _make_event(f"migrate:{task_key}", MIGRATED, 0, payload, None)


def migrate(
    config: ProjectConfig, directory: Path, task: dict[str, Any], *, dry_run: bool
) -> dict[str, Any]:
    """Add the versioned record fields and files; safe to run repeatedly."""
    task_key = task.get("task_key")
    if not isinstance(task_key, str) or not task_key:
        raise RecordError("RECORD", "task.json: task_key is missing", field="task_key")
    digest = intent_digest(task)
    event = _migrate_event(task_key, task, config)
    versioned = task.get("record_version") is not None

    if versioned:
        if task.get("record_version") != RECORD_VERSION:
            raise RecordError("RECORD", f"unsupported record_version {task.get('record_version')!r}",
                              field="record_version")
        stored = task.get("intent_digest")
        if stored != digest:
            raise RecordError(
                "CONFLICT",
                "intent fields changed since migration; restore the recorded intent",
                field="intent_digest",
                exit_code=EXIT_CONFLICT,
            )
        state = read_state(directory, task_key)
        events = read_events(directory)
        if state is None:
            if not events:
                raise RecordError("RECORD", f"{STATE_NAME} and {EVENTS_NAME} are both missing",
                                  field=STATE_NAME)
            if not dry_run:
                computed = replay_state(task_key, events)
                write_json_record(state_path(directory), computed)
                state = computed
            return {
                "ok": True, "task_key": task_key, "dry_run": dry_run, "migrated": False,
                "resumed": True, "record_version": RECORD_VERSION, "intent_digest": digest,
                "flow_version": task.get("flow_version"),
                "revision": None if dry_run else state["revision"],
                "phase": None if dry_run else state["phase"],
            }
        return {
            "ok": True, "task_key": task_key, "dry_run": dry_run, "migrated": False,
            "record_version": RECORD_VERSION, "intent_digest": digest,
            "flow_version": task.get("flow_version"),
            "revision": state["revision"], "phase": state["phase"],
        }

    preview = {
        "ok": True, "task_key": task_key, "dry_run": dry_run, "migrated": True,
        "intent_digest": digest, "flow_version": event["payload"]["flow_version"],
        "phase": task.get("phase"),
        "changes": {
            "task_json": list(RECORD_FIELDS),
            "create": [EVENTS_NAME, STATE_NAME],
        },
    }
    if dry_run:
        return preview

    events = read_events(directory)
    if events and events != [event]:
        raise RecordError(
            "CONFLICT",
            f"{EVENTS_NAME} already exists with different content",
            field=EVENTS_NAME,
            exit_code=EXIT_CONFLICT,
            suggestion="inspect the journal before retrying migration",
        )
    if not events:
        _write_events(directory, [event])
    state = replay_state(task_key, [event])
    write_json_record(state_path(directory), state)
    migrated_task = {
        **task,
        "record_version": RECORD_VERSION,
        "flow_version": event["payload"]["flow_version"],
        "intent_digest": digest,
    }
    write_json_record(directory / "task.json", migrated_task)
    return {
        **preview,
        "dry_run": False,
        "revision": state["revision"],
        "phase": state["phase"],
    }


def _payload_for(
    config: ProjectConfig, event_type: str, phase: str | None, summary: str | None
) -> dict[str, Any]:
    if event_type == PHASE_CHANGED:
        if not isinstance(phase, str) or not phase:
            raise RecordError("ARGS", "--phase is required for phase.changed", field="phase")
        phases = config.get_project_section().get("phases", [])
        if isinstance(phases, list) and phases and phase not in phases:
            raise RecordError("ARGS", f"phase must be one of {'/'.join(phases)}", field="phase")
        return {"phase": phase}
    if event_type == RESULT_RECORDED:
        if not isinstance(summary, str) or not summary.strip():
            raise RecordError("ARGS", "--summary is required for result.recorded", field="summary")
        return {"summary": summary}
    raise RecordError("ARGS", f"unsupported event type {event_type!r}", field="type")


def _append_event_payload(
    config: ProjectConfig,
    directory: Path,
    task: dict[str, Any],
    *,
    event_id: str,
    event_type: str,
    expected_revision: int,
    payload: dict[str, Any],
    dry_run: bool,
) -> dict[str, Any]:
    task_key = task.get("task_key")
    if not isinstance(task_key, str) or not task_key:
        raise RecordError("RECORD", "task.json: task_key is missing", field="task_key")
    if task.get("record_version") != RECORD_VERSION:
        raise RecordError(
            "RECORD", "task record is not versioned", field="record_version",
            suggestion=f"run `arch task migrate {task_key}` first",
        )
    if not EVENT_ID_RE.fullmatch(event_id):
        raise RecordError("ARGS", f"invalid --id {event_id!r}", field="event_id")
    state = read_state(directory, task_key)
    if state is None:
        raise RecordError("RECORD", f"{STATE_NAME} is missing", field=STATE_NAME,
                          suggestion=f"run `arch task replay {task_key}` to rebuild state")
    events = read_events(directory)

    for existing in events:
        if existing["event_id"] != event_id:
            continue
        same = (existing["type"] == event_type
                and existing["expected_revision"] == expected_revision
                and existing["payload"] == payload)
        if same:
            computed = replay_state(task_key, events)
            if computed != state and not dry_run:
                write_json_record(state_path(directory), computed)
            return {
                "ok": True, "task_key": task_key, "event_id": event_id,
                "duplicate": True, "revision": computed["revision"],
                "phase": computed["phase"], "flow_state": computed.get("flow_state"),
                "dry_run": dry_run,
            }
        raise RecordError(
            "CONFLICT",
            f"event {event_id!r} already exists with different content",
            field="event_id",
            exit_code=EXIT_CONFLICT,
            suggestion="use a new --id for a different transition",
        )

    if expected_revision != state["revision"]:
        raise RecordError(
            "CONFLICT",
            f"revision conflict: expected {expected_revision}, current {state['revision']}",
            field="expected_revision",
            exit_code=EXIT_CONFLICT,
            suggestion=f"re-read the record and retry with --expected-revision {state['revision']}",
        )

    event = _make_event(event_id, event_type, expected_revision, payload,
                        events[-1]["digest"] if events else None)
    new_events = [*events, event]
    new_state = replay_state(task_key, new_events)
    result = {
        "ok": True, "task_key": task_key, "event_id": event_id, "duplicate": False,
        "dry_run": dry_run, "revision": new_state["revision"], "phase": new_state["phase"],
        "flow_state": new_state.get("flow_state"),
    }
    if dry_run:
        return result
    _write_events(directory, new_events)
    write_json_record(state_path(directory), new_state)
    return result


def append_event(
    config: ProjectConfig,
    directory: Path,
    task: dict[str, Any],
    *,
    event_id: str,
    event_type: str,
    expected_revision: int,
    phase: str | None,
    summary: str | None,
    dry_run: bool,
) -> dict[str, Any]:
    """Append one phase or result event with idempotency and optimistic concurrency."""
    payload = _payload_for(config, event_type, phase, summary)
    return _append_event_payload(
        config, directory, task, event_id=event_id, event_type=event_type,
        expected_revision=expected_revision, payload=payload, dry_run=dry_run,
    )


def append_flow_transition(
    config: ProjectConfig,
    directory: Path,
    task: dict[str, Any],
    *,
    event_id: str,
    expected_revision: int,
    source: str,
    event: str,
    target: str,
    transition_id: str,
    dry_run: bool,
) -> dict[str, Any]:
    """Append one validated flow transition."""
    payload = {
        "from": source,
        "event": event,
        "to": target,
        "transition_id": transition_id,
    }
    return _append_event_payload(
        config, directory, task, event_id=event_id, event_type=FLOW_TRANSITIONED,
        expected_revision=expected_revision, payload=payload, dry_run=dry_run,
    )


def replay(
    config: ProjectConfig, directory: Path, task: dict[str, Any], *, dry_run: bool
) -> dict[str, Any]:
    """Rebuild ``state.json`` from the journal; the journal is authoritative."""
    task_key = task.get("task_key")
    if not isinstance(task_key, str) or not task_key:
        raise RecordError("RECORD", "task.json: task_key is missing", field="task_key")
    events = read_events(directory)
    if not events:
        raise RecordError("RECORD", f"{EVENTS_NAME} is missing or empty", field=EVENTS_NAME,
                          suggestion=f"run `arch task migrate {task_key}` first")
    computed = replay_state(task_key, events)
    if task.get("record_version") != RECORD_VERSION:
        raise RecordError(
            "RECORD", "task.json is not versioned but a journal exists",
            field="record_version",
            suggestion=f"run `arch task migrate {task_key}` to finish the versioned record",
        )
    if task.get("intent_digest") != computed["intent_digest"]:
        raise RecordError(
            "CONFLICT",
            "journal intent_digest does not match task.json",
            field="intent_digest",
            exit_code=EXIT_CONFLICT,
        )
    try:
        current = read_state(directory, task_key)
    except RecordError:
        current = None
    matches = current == computed
    if not dry_run and not matches:
        write_json_record(state_path(directory), computed)
    return {
        "ok": True, "task_key": task_key, "dry_run": dry_run, "restored": not matches,
        "revision": computed["revision"], "phase": computed["phase"],
        "event_count": computed["event_count"], "state_digest": computed["state_digest"],
    }


def record_errors(
    config: ProjectConfig, directory: Path, task: dict[str, Any], task_key: str
) -> list[str]:
    """Validate a versioned record; legacy records report no record errors."""
    if task.get("record_version") is None:
        return []
    errors: list[str] = []
    if task.get("record_version") != RECORD_VERSION:
        errors.append(f"task.json: unsupported record_version {task.get('record_version')!r}")
        return errors
    if "flow_version" not in task:
        errors.append("task.json: flow_version is missing for a versioned record")
    stored = task.get("intent_digest")
    if not isinstance(stored, str) or not stored.startswith("sha256:"):
        errors.append("task.json: intent_digest is missing or invalid")
    else:
        actual = intent_digest(task)
        if stored != actual:
            errors.append("task.json: intent fields changed since migration; intent is immutable")
    try:
        state = read_state(directory, task_key)
        events = read_events(directory)
    except RecordError as exc:
        errors.append(f"record: {exc}")
        return errors
    if state is None:
        errors.append(f"record: {STATE_NAME} is missing; run `arch task replay {task_key}`")
        return errors
    try:
        computed = replay_state(task_key, events)
    except RecordError as exc:
        errors.append(f"record: {exc}")
        return errors
    if computed != state:
        errors.append(f"record: {STATE_NAME} does not match {EVENTS_NAME}; "
                      f"run `arch task replay {task_key}`")
    if state.get("intent_digest") != stored:
        errors.append(f"record: {STATE_NAME} intent_digest does not match task.json")
    if state.get("flow_version") != task.get("flow_version"):
        errors.append(f"record: {STATE_NAME} flow_version does not match task.json")
    return errors
