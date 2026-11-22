"""Read-only analysis of local Kilo Code sessions.

The module turns the Kilo SQLite journal into a compact, drillable digest:

- find a session by a dialogue substring;
- label tool calls with workflow markers inferred from file paths and commands;
- aggregate tool outcomes, tokens, phases and anomalies;
- expose message/part references so an auditor can drill into a slice
  without re-reading the whole dialogue.

It is deterministic and never interprets the quality of the session. The
meaning of the result remains the agent's or owner's responsibility.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

DEFAULT_DB_PATH = "~/.local/share/kilo/kilo.db"
SCHEMA_VERSION = "kilo-session-digest-v1"

TEXT_PREVIEW = 4000
OUTPUT_PREVIEW = 4000
LARGE_OUTPUT_BYTES = 20000
MAX_MATCH_ROWS = 2000
MAX_ANOMALIES_PER_KIND = 20

ARCH_CLI_RE = re.compile(
    r"(?:^|[;&|(]\s*)(?:python[0-9.]*\s+)?"
    r"(?:(?:[^\s;&|]*/)?doc/tools/arch/__main__\.py|arch(?=\s))"
    r"\s+([^\s;&|]+)(?:\s+([^\s;&|]+))?"
)
COMMAND_PATH_RE = re.compile(
    r"(?<![\w.-])((?:doc|data|\.github|\.kilo)/[A-Za-z0-9._/-]+)"
)
GIT_RE = re.compile(r"\bgit\s+([a-z][a-z-]*)")
CLI_VERBS = {
    "task", "index", "docs", "session", "list", "show", "validate", "scan",
    "task-key", "--version", "--help",
}
TEST_RES = (
    (re.compile(r"run\.sh\b"), "test:run-sh"),
    (re.compile(r"\bunittest\b"), "test:unittest"),
    (re.compile(r"\bpytest\b"), "test:pytest"),
    (re.compile(r"\b(?:npm|pnpm|yarn)\s+(?:run\s+)?test\b"), "test:node"),
    (re.compile(r"\bcargo\s+test\b"), "test:cargo"),
    (re.compile(r"\bgo\s+test\b"), "test:go"),
)
TASK_CONF_RE = re.compile(r"doc/config/task-conf/types/([^/]+)(?:/(.*))?$")
TASK_RE = re.compile(
    r"doc/tasks/([^/]+)(?:/subtasks/([0-9]{4}))?(?:/(stage[0-9]+))?(?:/(.*))?$"
)
SKILL_RE = re.compile(r"doc/skills/([^/]+)/SKILL\.md$")


def resolve_db_path(explicit: str | Path | None = None) -> Path:
    """Return the Kilo database path without opening it."""
    if explicit:
        return Path(explicit).expanduser()
    env = os.environ.get("KILO_AUDIT_DB")
    if env:
        return Path(env).expanduser()
    return Path(DEFAULT_DB_PATH).expanduser()


def open_db(path: str | Path) -> sqlite3.Connection:
    """Open the Kilo database strictly read-only."""
    resolved = Path(path).expanduser().resolve(strict=True)
    connection = sqlite3.connect(resolved.as_uri() + "?mode=ro", uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def find_sessions(
    db: sqlite3.Connection,
    query: str,
    *,
    directory: str | Path | None = None,
    all_projects: bool = False,
    role: str = "any",
    limit: int = 20,
) -> dict[str, Any]:
    """Find sessions whose text parts contain ``query`` as a substring."""
    if not query or not query.strip():
        raise ValueError("search text must not be empty")
    if role not in {"any", "user", "assistant"}:
        raise ValueError("role must be any, user or assistant")

    pattern = "%" + _escape_like(query.strip()) + "%"
    where = [
        "json_extract(p.data, '$.type') = 'text'",
        "coalesce(json_extract(p.data, '$.synthetic'), 0) = 0",
        "coalesce(json_extract(p.data, '$.ignored'), 0) = 0",
        "json_extract(p.data, '$.text') LIKE ? ESCAPE '\\'",
    ]
    params: list[Any] = [pattern]
    if role != "any":
        where.append("json_extract(m.data, '$.role') = ?")
        params.append(role)
    if not all_projects and directory is not None:
        where.append(
            "p.session_id IN ("
            "SELECT id FROM session WHERE directory = ? OR project_id = ("
            "SELECT project_id FROM session WHERE directory = ? "
            "ORDER BY time_updated DESC LIMIT 1))"
        )
        params.extend([str(directory), str(directory)])

    sql = (
        "SELECT p.session_id AS session_id, p.message_id AS message_id, "
        "p.id AS part_id, substr(json_extract(p.data, '$.text'), 1, 320) AS snippet, "
        "json_extract(m.data, '$.role') AS role, m.time_created AS message_ms "
        "FROM part p JOIN message m "
        "ON m.id = p.message_id AND m.session_id = p.session_id "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY p.session_id, m.time_created, p.id "
        f"LIMIT {MAX_MATCH_ROWS + 1}"
    )
    rows = db.execute(sql, params).fetchall()
    truncated = len(rows) > MAX_MATCH_ROWS
    rows = rows[:MAX_MATCH_ROWS]

    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        entry = grouped.setdefault(
            row["session_id"],
            {"match_count": 0, "message_ids": [], "first_match": None, "last_match_ms": 0},
        )
        entry["match_count"] += 1
        entry["last_match_ms"] = max(entry["last_match_ms"], row["message_ms"] or 0)
        if row["message_id"] not in entry["message_ids"]:
            entry["message_ids"].append(row["message_id"])
        if entry["first_match"] is None:
            entry["first_match"] = {
                "message_id": row["message_id"],
                "part_id": row["part_id"],
                "role": row["role"],
                "snippet": row["snippet"],
            }

    sessions: list[dict[str, Any]] = []
    if grouped:
        placeholders = ", ".join("?" for _ in grouped)
        meta_rows = db.execute(
            "SELECT id, parent_id, title, directory, agent, version, "
            "time_created, time_updated FROM session "
            f"WHERE id IN ({placeholders})",
            list(grouped),
        ).fetchall()
        for meta in meta_rows:
            item = grouped[meta["id"]]
            sessions.append(
                {
                    "id": meta["id"],
                    "parent_id": meta["parent_id"],
                    "title": meta["title"],
                    "directory": meta["directory"],
                    "agent": meta["agent"],
                    "version": meta["version"],
                    "created_at": _iso(meta["time_created"]),
                    "updated_at": _iso(meta["time_updated"]),
                    "last_match_at": _iso(item["last_match_ms"]),
                    "match_count": item["match_count"],
                    "matched_message_ids": item["message_ids"],
                    "first_match": item["first_match"],
                }
            )
        sessions.sort(
            key=lambda item: (
                item["last_match_at"] or "",
                item["updated_at"] or "",
                item["id"],
            ),
            reverse=True,
        )

    return {
        "schema": "kilo-session-find-v1",
        "query": query.strip(),
        "role": role,
        "scope": "all" if all_projects else "project",
        "directory": None if all_projects or directory is None else str(directory),
        "truncated": truncated,
        "sessions": sessions[: max(0, limit)],
    }


def digest_session(
    db: sqlite3.Connection,
    session_id: str,
    *,
    root: str | Path | None = None,
    max_events: int = 1000,
    full_text: bool = False,
    include_children: bool = True,
) -> dict[str, Any]:
    """Build a compact, drillable digest of one session."""
    session_row = db.execute("SELECT * FROM session WHERE id = ?", (session_id,)).fetchone()
    if session_row is None:
        raise ValueError(f"session not found: {session_id}")
    session = dict(session_row)
    root_path = Path(root or session.get("directory") or ".")

    message_rows = db.execute(
        "SELECT id, time_created, data FROM message "
        "WHERE session_id = ? ORDER BY time_created, id",
        (session_id,),
    ).fetchall()
    messages = [_message_info(row) for row in message_rows]

    part_rows = db.execute(
        "SELECT p.id AS part_id, p.message_id AS message_id, p.time_created AS part_ms, "
        "m.time_created AS message_ms, json_extract(m.data, '$.role') AS role, "
        "p.data AS data "
        "FROM part p JOIN message m "
        "ON m.id = p.message_id AND m.session_id = p.session_id "
        "WHERE p.session_id = ? "
        "ORDER BY m.time_created, m.id, p.time_created, p.id",
        (session_id,),
    ).fetchall()

    tokens_by_message = {m["id"]: m["tokens"] for m in messages}
    events: list[dict[str, Any]] = []
    user_messages: list[dict[str, Any]] = []
    assistant_texts: list[dict[str, Any]] = []
    seq = 0

    for row in part_rows:
        data = _loads(row["data"])
        if not isinstance(data, dict):
            continue
        part_type = data.get("type")
        role = row["role"]
        if part_type == "text":
            if data.get("synthetic") or data.get("ignored"):
                continue
            text = data.get("text") or ""
            if not text.strip():
                continue
            seq += 1
            if role == "user":
                item = {
                    "message_id": row["message_id"],
                    "part_id": row["part_id"],
                    "at": _iso(row["message_ms"]),
                    "text": _clip(text, TEXT_PREVIEW, full_text),
                    "text_bytes": len(text.encode("utf-8")),
                    "truncated": not full_text and len(text) > TEXT_PREVIEW,
                }
                user_messages.append(item)
                events.append(
                    {
                        "seq": seq,
                        "kind": "user",
                        "message_id": row["message_id"],
                        "part_id": row["part_id"],
                        "at": _iso(row["message_ms"]),
                        "text": item["text"],
                        "text_bytes": item["text_bytes"],
                        "truncated": item["truncated"],
                    }
                )
            else:
                item = {
                    "message_id": row["message_id"],
                    "part_id": row["part_id"],
                    "at": _iso(row["message_ms"]),
                    "text": _clip(text, TEXT_PREVIEW, full_text),
                    "text_bytes": len(text.encode("utf-8")),
                    "truncated": not full_text and len(text) > TEXT_PREVIEW,
                    "tokens": tokens_by_message.get(row["message_id"]),
                }
                assistant_texts.append(item)
                events.append(
                    {
                        "seq": seq,
                        "kind": "assistant",
                        "message_id": row["message_id"],
                        "part_id": row["part_id"],
                        "at": _iso(row["message_ms"]),
                        "text": item["text"],
                        "text_bytes": item["text_bytes"],
                        "truncated": item["truncated"],
                        "tokens_total": (tokens_by_message.get(row["message_id"]) or {}).get("total"),
                    }
                )
        elif part_type == "tool":
            seq += 1
            events.append(_tool_event(seq, row, data, root_path))
        elif part_type == "file":
            seq += 1
            source = data.get("source") or {}
            target = source.get("path") or data.get("filename") or source.get("name")
            labels = _labels_for_paths(
                [_project_relative(target, root_path)] if target else [], root_path
            )
            events.append(
                {
                    "seq": seq,
                    "kind": "file",
                    "message_id": row["message_id"],
                    "part_id": row["part_id"],
                    "at": _iso(row["message_ms"]),
                    "target": target,
                    "labels": labels,
                }
            )

    tokens = _sum_tokens(messages)
    tool_stats = _tool_stats(events)
    activities = _activity_counts(events)
    markers = _markers(events)
    label_index = _label_index(events)
    phases = _phases(events)
    anomalies = _anomalies(events)

    timeline, omitted = _timeline(events, max_events)
    final_answer = _final_answer(assistant_texts, full_text)

    return {
        "schema": SCHEMA_VERSION,
        "session": {
            "id": session["id"],
            "title": session.get("title"),
            "directory": session.get("directory"),
            "parent_id": session.get("parent_id"),
            "agent": session.get("agent"),
            "version": session.get("version"),
            "models": _models(session, messages),
            "started_at": _iso(session.get("time_created")),
            "updated_at": _iso(session.get("time_updated")),
            "last_message_at": messages[-1]["at"] if messages else None,
            "message_count": len(messages),
            "user_message_count": sum(1 for m in messages if m["role"] == "user"),
            "assistant_message_count": sum(1 for m in messages if m["role"] == "assistant"),
            "part_count": len(part_rows),
            "event_count": len(events),
            "tool_call_count": sum(1 for e in events if e["kind"] == "tool"),
            "tokens": tokens,
            "children": _children(db, session_id) if include_children else [],
        },
        "dialog": {
            "user_messages": user_messages,
            "assistant_text_count": len(assistant_texts),
            "final_answer": final_answer,
        },
        "stats": {"tools": tool_stats, "activities": activities},
        "tool_calls": _compact_tool_calls(events),
        "markers": markers,
        "timeline": timeline,
        "timeline_omitted": omitted,
        "label_index": label_index,
        "phases": phases,
        "anomalies": anomalies,
        "drill": {
            "session_id": session_id,
            "events": f"arch session events {session_id} --message <message_id> --json",
            "find": "arch session find --match <text> --json",
        },
    }


def session_events(
    db: sqlite3.Connection,
    session_id: str,
    *,
    message_id: str | None = None,
    part_id: str | None = None,
    offset: int = 0,
    limit: int = 100,
    full: bool = False,
) -> dict[str, Any]:
    """Return a drill-down slice of a session as raw-ish events."""
    where = ["p.session_id = ?"]
    params: list[Any] = [session_id]
    if message_id:
        where.append("p.message_id = ?")
        params.append(message_id)
    if part_id:
        where.append("p.id = ?")
        params.append(part_id)

    rows = db.execute(
        "SELECT p.id AS part_id, p.message_id AS message_id, p.time_created AS part_ms, "
        "m.time_created AS message_ms, json_extract(m.data, '$.role') AS role, "
        "p.data AS data, count(*) OVER () AS total "
        "FROM part p JOIN message m "
        "ON m.id = p.message_id AND m.session_id = p.session_id "
        f"WHERE {' AND '.join(where)} "
        "ORDER BY m.time_created, m.id, p.time_created, p.id "
        "LIMIT ? OFFSET ?",
        params + [max(1, limit), max(0, offset)],
    ).fetchall()

    total = rows[0]["total"] if rows else 0
    events: list[dict[str, Any]] = []
    for index, row in enumerate(rows, start=offset + 1):
        data = _loads(row["data"])
        if not isinstance(data, dict):
            continue
        item = _drill_event(index, row, data, full)
        if item is not None:
            events.append(item)

    return {
        "schema": "kilo-session-events-v1",
        "session_id": session_id,
        "message_id": message_id,
        "part_id": part_id,
        "offset": offset,
        "limit": limit,
        "total": total,
        "events": events,
    }


# --- event construction -------------------------------------------------


def _tool_event(
    seq: int, row: sqlite3.Row, data: dict[str, Any], root: Path
) -> dict[str, Any]:
    tool = data.get("tool") or "unknown"
    state = data.get("state") or {}
    inp = state.get("input") or {}
    metadata = state.get("metadata") or {}
    output = state.get("output")
    if not isinstance(output, str):
        output = metadata.get("output")
    output_bytes = len(output.encode("utf-8")) if isinstance(output, str) else 0
    exit_code = _exit_code(metadata)
    outcome = _outcome(state, exit_code)
    target = _tool_target(tool, inp)
    if target and tool in {"read", "write", "edit", "glob", "grep", "list"}:
        target = _project_relative(target, root)
    labels = _labels_for_tool(tool, inp, root)
    timing = state.get("time") or {}

    event: dict[str, Any] = {
        "seq": seq,
        "kind": "tool",
        "tool": tool,
        "message_id": row["message_id"],
        "part_id": row["part_id"],
        "at": _iso(row["message_ms"]),
        "status": state.get("status"),
        "outcome": outcome,
    }
    if target:
        event["target"] = target
    if exit_code is not None:
        event["exit_code"] = exit_code
    if output_bytes:
        event["output_bytes"] = output_bytes
    if labels:
        event["labels"] = labels
    if timing.get("start") and timing.get("end"):
        event["duration_ms"] = max(0, timing["end"] - timing["start"])
    error = state.get("error")
    if isinstance(error, str) and error:
        event["error"] = _clip(error, 500, False)
    return event


def _drill_event(
    seq: int, row: sqlite3.Row, data: dict[str, Any], full: bool
) -> dict[str, Any] | None:
    part_type = data.get("type")
    if part_type == "text":
        if data.get("synthetic") or data.get("ignored"):
            return None
        text = data.get("text") or ""
        return {
            "seq": seq,
            "kind": "text",
            "message_id": row["message_id"],
            "part_id": row["part_id"],
            "role": row["role"],
            "at": _iso(row["message_ms"]),
            "text": _clip(text, OUTPUT_PREVIEW, full),
            "text_bytes": len(text.encode("utf-8")),
            "truncated": not full and len(text) > OUTPUT_PREVIEW,
        }
    if part_type == "tool":
        state = data.get("state") or {}
        inp = state.get("input") or {}
        metadata = state.get("metadata") or {}
        output = state.get("output")
        if not isinstance(output, str):
            output = metadata.get("output")
        exit_code = _exit_code(metadata)
        return {
            "seq": seq,
            "kind": "tool",
            "tool": data.get("tool"),
            "message_id": row["message_id"],
            "part_id": row["part_id"],
            "at": _iso(row["message_ms"]),
            "status": state.get("status"),
            "outcome": _outcome(state, exit_code),
            "exit_code": exit_code,
            "target": _tool_target(data.get("tool") or "", inp),
            "input": inp,
            "output": _clip(output, OUTPUT_PREVIEW, full) if isinstance(output, str) else None,
            "output_bytes": len(output.encode("utf-8")) if isinstance(output, str) else 0,
            "truncated": not full and isinstance(output, str) and len(output) > OUTPUT_PREVIEW,
        }
    if part_type == "file":
        source = data.get("source") or {}
        return {
            "seq": seq,
            "kind": "file",
            "message_id": row["message_id"],
            "part_id": row["part_id"],
            "at": _iso(row["message_ms"]),
            "target": source.get("path") or data.get("filename"),
        }
    return None


# --- markers ------------------------------------------------------------


def _labels_for_tool(tool: str, inp: dict[str, Any], root: Path) -> list[str]:
    paths: list[str] = []
    if tool in {"read", "write", "edit"}:
        value = inp.get("filePath") or inp.get("path")
        if isinstance(value, str):
            paths.append(value)
    elif tool in {"glob", "grep", "list"}:
        value = inp.get("path")
        if isinstance(value, str):
            paths.append(value)
    elif tool == "bash":
        command = inp.get("command")
        if isinstance(command, str):
            paths.extend(COMMAND_PATH_RE.findall(command))

    labels = _labels_for_paths([_project_relative(p, root) for p in paths], root)
    if tool == "skill":
        name = inp.get("name")
        if isinstance(name, str) and name:
            labels.append(f"skill:{name}")
    if tool == "bash":
        command = inp.get("command")
        if isinstance(command, str):
            labels.extend(_command_labels(command))
    return _dedupe(labels)


def _labels_for_paths(paths: Iterable[str], root: Path) -> list[str]:
    labels: list[str] = []
    for raw in paths:
        rel = _project_relative(raw, root).lstrip("./")
        if not rel:
            continue
        match = SKILL_RE.search(rel)
        if match:
            labels.append(f"skill:{match.group(1)}")
        if rel == "doc/skills/README.md":
            labels.append("skills-index")
        match = TASK_CONF_RE.search(rel)
        if match:
            task_type, rest = match.group(1), match.group(2) or ""
            labels.append(f"type:{task_type}")
            flow_match = re.match(r"flows/([^/]+)(?:/(.*))?$", rest)
            if flow_match:
                flow, tail = flow_match.group(1), flow_match.group(2) or ""
                labels.append(f"flow:{task_type}/{flow}")
                step_match = re.match(r"stepsprompt/([^/]+)\.md$", tail)
                if step_match:
                    labels.append(f"flow-step:{task_type}/{flow}/{step_match.group(1)}")
        match = TASK_RE.search(rel)
        if match:
            key, subtask, stage, artifact = match.groups()
            labels.append(f"task:{key}")
            if subtask:
                labels.append(f"subtask:{key}/{subtask}")
            if stage:
                labels.append(f"stage:{stage}")
            if artifact:
                labels.append(f"artifact:{artifact}")
        if rel in {"AGENTS.md", "doc/AGENTS.md", "README.md", "doc/skills/README.md"}:
            labels.append(f"rule:{rel}")
        if rel.startswith("doc/architecture/") and _looks_like_file(rel):
            labels.append(f"arch:{rel}")
            doc_id = _arch_doc_id(root, rel)
            if doc_id:
                labels.append(f"arch-id:{doc_id}")
            flow_match = re.match(r"doc/architecture/domains/([^/]+)/flows/([^/]+)\.md$", rel)
            if flow_match:
                labels.append(f"arch-flow:{flow_match.group(1)}/{flow_match.group(2)}")
            domain_flow = re.match(r"doc/architecture/domains/([^/]+)/flow\.md$", rel)
            if domain_flow:
                labels.append(f"arch-flow:{domain_flow.group(1)}")
            part_match = re.match(
                r"doc/architecture/domains/([^/]+)/(capabilities|entities)/([^/]+)\.md$",
                rel,
            )
            if part_match:
                labels.append(
                    f"arch-{part_match.group(2)[:-1]}:{part_match.group(1)}/{part_match.group(3)}"
                )
        if rel == "doc/config/paths.yaml":
            labels.append("config:paths")
        if rel.startswith("data/"):
            labels.append(f"ref:{rel}")
        if rel.startswith("doc/tools/") and _looks_like_file(rel):
            labels.append(f"cli-source:{rel}")
        if rel.endswith("run.sh"):
            labels.append("test:run-sh")
    return _dedupe(labels)


def _command_labels(command: str) -> list[str]:
    labels: list[str] = []
    match = ARCH_CLI_RE.search(command)
    if match:
        first, second = match.group(1), match.group(2)
        if first not in CLI_VERBS:
            return labels
        if first in {"task", "index", "docs", "session"} and second and not second.startswith("-"):
            labels.append(f"cli:{first} {second}")
        else:
            labels.append(f"cli:{first}")
    match = GIT_RE.search(command)
    if match:
        labels.append(f"git:{match.group(1)}")
    for pattern, label in TEST_RES:
        if pattern.search(command):
            labels.append(label)
    if "kilo db path" in command:
        labels.append("kilo:db")
    return labels


def _markers(events: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    raw: dict[str, dict[str, Any]] = {}
    for event in events:
        for label in event.get("labels") or []:
            entry = raw.get(label)
            if entry is None:
                entry = {
                    "label": label,
                    "count": 0,
                    "first_seq": event["seq"],
                    "first_message_id": event["message_id"],
                    "success": 0,
                    "failure": 0,
                    "via": set(),
                }
                raw[label] = entry
            entry["count"] += 1
            if event.get("outcome") == "success":
                entry["success"] += 1
            elif event.get("outcome") == "failure":
                entry["failure"] += 1
            if label.startswith("skill:"):
                entry["via"].add("skill-tool" if event.get("tool") == "skill" else "read")

    groups: dict[str, list[dict[str, Any]]] = {
        "skills": [],
        "rules": [],
        "flows": [],
        "flow_steps": [],
        "task_types": [],
        "tasks": [],
        "subtasks": [],
        "stages": [],
        "architecture": [],
        "architecture_flows": [],
        "cli": [],
        "tests": [],
        "references": [],
    }
    arch_ids_by_path: dict[str, str] = {}
    for event in events:
        labels = event.get("labels") or []
        doc_id = next((item.split(":", 1)[1] for item in labels if item.startswith("arch-id:")), None)
        for item in labels:
            if item.startswith("arch:") and doc_id:
                arch_ids_by_path[item.split(":", 1)[1]] = doc_id

    for label, entry in raw.items():
        kind, _, value = label.partition(":")
        base = {
            "label": label,
            "count": entry["count"],
            "first_seq": entry["first_seq"],
            "first_message_id": entry["first_message_id"],
        }
        if kind == "skill":
            groups["skills"].append({**base, "id": value, "via": sorted(entry["via"])})
        elif kind == "rule":
            groups["rules"].append({**base, "path": value})
        elif kind == "flow":
            task_type, _, flow = value.partition("/")
            groups["flows"].append({**base, "type": task_type, "flow": flow})
        elif kind == "flow-step":
            task_type, _, rest = value.partition("/")
            flow, _, step = rest.partition("/")
            groups["flow_steps"].append(
                {**base, "type": task_type, "flow": flow, "step": step}
            )
        elif kind == "type":
            groups["task_types"].append({**base, "type": value})
        elif kind == "task":
            groups["tasks"].append({**base, "task_key": value})
        elif kind == "subtask":
            key, _, subtask = value.partition("/")
            groups["subtasks"].append({**base, "task_key": key, "subtask": subtask})
        elif kind == "stage":
            groups["stages"].append({**base, "stage": value})
        elif kind == "arch":
            item = {**base, "path": value}
            if value in arch_ids_by_path:
                item["doc_id"] = arch_ids_by_path[value]
            groups["architecture"].append(item)
        elif kind == "arch-flow":
            domain, _, flow = value.partition("/")
            groups["architecture_flows"].append({**base, "domain": domain, "flow": flow})
        elif kind == "arch-capability":
            domain, _, slug = value.partition("/")
            groups["architecture"].append(
                {**base, "path": value, "kind": "capability", "domain": domain, "slug": slug}
            )
        elif kind == "arch-entity":
            domain, _, slug = value.partition("/")
            groups["architecture"].append(
                {**base, "path": value, "kind": "entity", "domain": domain, "slug": slug}
            )
        elif kind == "arch-id":
            continue
        elif kind == "cli":
            groups["cli"].append(
                {
                    **base,
                    "command": value,
                    "success": entry["success"],
                    "failure": entry["failure"],
                }
            )
        elif kind == "test":
            groups["tests"].append({**base, "kind": value})
        elif kind == "ref":
            groups["references"].append({**base, "path": value})

    for items in groups.values():
        items.sort(key=lambda item: (item["first_seq"], item["label"]))
    return groups


def _label_index(events: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for event in events:
        for label in event.get("labels") or []:
            entry = index.setdefault(label, {"count": 0, "refs": []})
            entry["count"] += 1
            if len(entry["refs"]) < 20:
                entry["refs"].append(
                    {
                        "seq": event["seq"],
                        "message_id": event["message_id"],
                        "part_id": event["part_id"],
                    }
                )
    return index


def _phases(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for event in events:
        if event["kind"] != "tool":
            continue
        activity = _activity(event)
        if segments and segments[-1]["activity"] == activity:
            segment = segments[-1]
            segment["to_seq"] = event["seq"]
            segment["to_message_id"] = event["message_id"]
            segment["tool_calls"] += 1
        else:
            segments.append(
                {
                    "activity": activity,
                    "from_seq": event["seq"],
                    "to_seq": event["seq"],
                    "from_message_id": event["message_id"],
                    "to_message_id": event["message_id"],
                    "tool_calls": 1,
                }
            )
    return segments


def _activity_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        if event["kind"] != "tool":
            continue
        activity = _activity(event)
        counts[activity] = counts.get(activity, 0) + 1
    return dict(sorted(counts.items()))


def _activity(event: dict[str, Any]) -> str:
    tool = event.get("tool")
    labels = event.get("labels") or []
    if tool in {"write", "edit"}:
        return "edit"
    if any(label.startswith("test:") for label in labels) or any(
        label in {"cli:task evidence", "cli:task close"} for label in labels
    ):
        return "verify"
    if tool in {"read", "grep", "glob", "list", "skill"}:
        return "explore"
    if tool == "bash":
        if any(label.startswith("git:") for label in labels):
            return "explore"
        return "execute"
    return "other"


def _anomalies(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    anomalies: list[dict[str, Any]] = []

    for event in events:
        if event["kind"] != "tool":
            continue
        if event.get("outcome") == "failure":
            anomalies.append(
                {
                    "kind": "failed_tool",
                    "seq": event["seq"],
                    "message_id": event["message_id"],
                    "tool": event.get("tool"),
                    "target": event.get("target"),
                    "exit_code": event.get("exit_code"),
                    "error": event.get("error"),
                }
            )
        if event.get("output_bytes", 0) >= LARGE_OUTPUT_BYTES:
            anomalies.append(
                {
                    "kind": "large_output",
                    "seq": event["seq"],
                    "message_id": event["message_id"],
                    "tool": event.get("tool"),
                    "target": event.get("target"),
                    "output_bytes": event["output_bytes"],
                }
            )

    reads: dict[str, list[int]] = {}
    commands: dict[str, list[int]] = {}
    for event in events:
        if event["kind"] != "tool":
            continue
        if event.get("tool") in {"read", "grep", "glob"} and event.get("target"):
            reads.setdefault(str(event["target"]), []).append(event["seq"])
        if event.get("tool") == "bash" and event.get("target"):
            commands.setdefault(str(event["target"]), []).append(event["seq"])

    for path, seqs in reads.items():
        if len(seqs) > 1:
            anomalies.append(
                {"kind": "repeated_read", "target": path, "count": len(seqs), "seqs": seqs}
            )
    for command, seqs in commands.items():
        if len(seqs) > 1:
            anomalies.append(
                {
                    "kind": "repeated_command",
                    "target": command,
                    "count": len(seqs),
                    "seqs": seqs,
                }
            )

    counts: dict[str, int] = {}
    limited: list[dict[str, Any]] = []
    for item in anomalies:
        kind = item["kind"]
        counts[kind] = counts.get(kind, 0) + 1
        if counts[kind] <= MAX_ANOMALIES_PER_KIND:
            limited.append(item)
    return limited


# --- aggregation helpers ------------------------------------------------


def _message_info(row: sqlite3.Row) -> dict[str, Any]:
    data = _loads(row["data"]) or {}
    tokens = data.get("tokens") or {}
    cache = tokens.get("cache") or {}
    return {
        "id": row["id"],
        "role": data.get("role"),
        "model": data.get("modelID"),
        "provider": data.get("providerID"),
        "at": _iso(row["time_created"]),
        "tokens": {
            "input": _int(tokens.get("input")),
            "output": _int(tokens.get("output")),
            "reasoning": _int(tokens.get("reasoning")),
            "cache_read": _int(cache.get("read")),
            "cache_write": _int(cache.get("write")),
            "total": _int(tokens.get("total")),
        },
        "cost": data.get("cost") or 0,
    }


def _sum_tokens(messages: list[dict[str, Any]]) -> dict[str, Any]:
    total = {
        "input": 0,
        "output": 0,
        "reasoning": 0,
        "cache_read": 0,
        "cache_write": 0,
        "total": 0,
        "cost": 0.0,
    }
    for message in messages:
        if message["role"] != "assistant":
            continue
        for key in ("input", "output", "reasoning", "cache_read", "cache_write", "total"):
            total[key] += message["tokens"][key]
        total["cost"] += message["cost"]
    return total


def _compact_tool_calls(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for event in events:
        if event["kind"] != "tool":
            continue
        item: dict[str, Any] = {
            "seq": event["seq"],
            "message_id": event["message_id"],
            "part_id": event["part_id"],
            "tool": event.get("tool"),
            "outcome": event.get("outcome"),
        }
        if event.get("exit_code") is not None:
            item["exit_code"] = event["exit_code"]
        if event.get("target"):
            item["target"] = _clip(event["target"], 240, False)
        if event.get("output_bytes"):
            item["output_bytes"] = event["output_bytes"]
        if event.get("labels"):
            item["labels"] = event["labels"]
        calls.append(item)
    return calls


def _tool_stats(events: list[dict[str, Any]]) -> dict[str, Any]:
    by_tool: dict[str, dict[str, Any]] = {}
    outcomes = {"success": 0, "failure": 0, "unknown": 0}
    for event in events:
        if event["kind"] != "tool":
            continue
        tool = event.get("tool") or "unknown"
        entry = by_tool.setdefault(
            tool,
            {"calls": 0, "success": 0, "failure": 0, "unknown": 0, "output_bytes": 0},
        )
        entry["calls"] += 1
        outcome = event.get("outcome") or "unknown"
        entry[outcome] = entry.get(outcome, 0) + 1
        outcomes[outcome] = outcomes.get(outcome, 0) + 1
        entry["output_bytes"] += event.get("output_bytes", 0)
    return {
        "total": sum(item["calls"] for item in by_tool.values()),
        "outcomes": outcomes,
        "by_tool": dict(sorted(by_tool.items())),
    }


def _children(db: sqlite3.Connection, session_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        "SELECT id, title, time_created, time_updated, tokens_input, tokens_output, "
        "tokens_reasoning, tokens_cache_read, tokens_cache_write, cost "
        "FROM session WHERE parent_id = ? ORDER BY time_created, id",
        (session_id,),
    ).fetchall()
    children: list[dict[str, Any]] = []
    for row in rows:
        tool_calls = db.execute(
            "SELECT count(*) FROM part WHERE session_id = ? "
            "AND json_extract(data, '$.type') = 'tool'",
            (row["id"],),
        ).fetchone()[0]
        children.append(
            {
                "id": row["id"],
                "title": row["title"],
                "started_at": _iso(row["time_created"]),
                "updated_at": _iso(row["time_updated"]),
                "tool_calls": tool_calls,
                "tokens_total": sum(
                    _int(row[key])
                    for key in (
                        "tokens_input",
                        "tokens_output",
                        "tokens_reasoning",
                        "tokens_cache_read",
                        "tokens_cache_write",
                    )
                ),
                "cost": row["cost"] or 0,
            }
        )
    return children


def _models(session: dict[str, Any], messages: list[dict[str, Any]]) -> list[str]:
    models: list[str] = []
    raw = session.get("model")
    if isinstance(raw, str) and raw:
        parsed = _loads(raw)
        if isinstance(parsed, dict):
            name = parsed.get("id") or parsed.get("modelID")
            provider = parsed.get("providerID")
            if name:
                models.append(f"{provider}/{name}" if provider else str(name))
        else:
            models.append(raw)
    for message in messages:
        if message.get("provider") and message.get("model"):
            value = f"{message['provider']}/{message['model']}"
            if value not in models:
                models.append(value)
        elif message.get("model") and message["model"] not in models:
            models.append(message["model"])
    return models


def _timeline(
    events: list[dict[str, Any]], max_events: int
) -> tuple[list[dict[str, Any]], int]:
    if not max_events or len(events) <= max_events:
        return events, 0
    head_count = max(1, max_events // 2)
    tail_count = max(1, max_events - head_count)
    omitted = len(events) - head_count - tail_count
    timeline = list(events[:head_count])
    timeline.append(
        {
            "kind": "omitted",
            "count": omitted,
            "note": "use arch session events --offset <n> --limit <n> to read the gap",
        }
    )
    timeline.extend(events[-tail_count:])
    return timeline, omitted


def _final_answer(
    assistant_texts: list[dict[str, Any]], full_text: bool
) -> dict[str, Any] | None:
    if not assistant_texts:
        return None
    item = assistant_texts[-1]
    return {
        "message_id": item["message_id"],
        "part_id": item["part_id"],
        "at": item["at"],
        "text": _clip(item["text"], TEXT_PREVIEW, full_text),
        "text_bytes": item["text_bytes"],
        "truncated": item["truncated"],
        "tokens": item.get("tokens"),
    }


# --- small utilities ----------------------------------------------------


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _loads(value: Any) -> Any:
    if not isinstance(value, str):
        return None
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return None


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _exit_code(metadata: dict[str, Any]) -> int | None:
    value = metadata.get("exit")
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _outcome(state: dict[str, Any], exit_code: int | None) -> str:
    status = state.get("status")
    if status in {"error", "failed"}:
        return "failure"
    if exit_code not in (None, 0):
        return "failure"
    if status in {"pending", "running"}:
        return "unknown"
    if status == "completed":
        return "success"
    return "unknown"


def _tool_target(tool: str, inp: dict[str, Any]) -> str | None:
    if tool in {"read", "write", "edit"}:
        return inp.get("filePath") or inp.get("path")
    if tool in {"glob", "grep", "list"}:
        return inp.get("path") or inp.get("pattern")
    if tool == "bash":
        return inp.get("command")
    if tool == "skill":
        return inp.get("name")
    if tool == "webfetch":
        return inp.get("url")
    if tool == "task":
        return inp.get("description")
    return None


def _project_relative(path: str | Path | None, root: Path) -> str:
    if path is None:
        return ""
    raw = str(path).replace("\\", "/")
    if not raw:
        return ""
    root_raw = str(root).replace("\\", "/").rstrip("/")
    if root_raw and raw.startswith(root_raw + "/"):
        return raw[len(root_raw) + 1 :]
    for marker in ("/doc/", "/data/", "/.github/", "/.kilo/"):
        index = raw.find(marker)
        if index >= 0:
            return raw[index + 1 :]
    return raw


@lru_cache(maxsize=512)
def _arch_doc_id(root: str, rel: str) -> str | None:
    path = Path(root) / rel
    try:
        with path.open(encoding="utf-8") as handle:
            in_frontmatter = False
            for index, line in enumerate(handle):
                stripped = line.strip()
                if index == 0:
                    if stripped != "---":
                        return None
                    in_frontmatter = True
                    continue
                if stripped == "---":
                    break
                if in_frontmatter:
                    match = re.match(r"id:\s*(.+)", stripped)
                    if match:
                        return match.group(1).strip().strip("\"'")
                if index > 60:
                    break
    except OSError:
        return None
    return None


def _iso(milliseconds: Any) -> str | None:
    try:
        value = int(milliseconds)
    except (TypeError, ValueError):
        return None
    if value <= 0:
        return None
    return (
        datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _clip(value: Any, limit: int, full: bool) -> str | None:
    if value is None:
        return None
    text = value if isinstance(value, str) else str(value)
    if full or len(text) <= limit:
        return text
    return text[:limit]


def _looks_like_file(rel: str) -> bool:
    return bool(Path(rel).suffix)


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result
