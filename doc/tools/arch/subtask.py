"""Subtask directory and scaffold helpers.

Subtasks are always manual — no external source binding. A subtask id is unique
only within its parent task; recursion is allowed (a subtask may have its own
subtasks/).
"""

from __future__ import annotations

from pathlib import Path

from .schema import scaffold_task_json
from .identity import task_dir


def subtask_dir(root, parent_task_key: str, subtask_id: str) -> Path:
    """Return the canonical subtask directory path."""
    return task_dir(root, parent_task_key) / "subtasks" / subtask_id


def scaffold_subtask_json(
    parent_task_key: str,
    subtask_id: str,
    subtask_title: str | None = None,
    *,
    task_type: str | None = None,
    flow: str | None = None,
    complexity: str | None = None,
    estimate_hours: float | None = None,
) -> str:
    """Build a subtask task.json from the shape chosen by the agent.

    The agent decides the work shape. Callers pass the parent's values as a
    default and may override them per child; nothing is hardcoded to a
    scaffold-only record.
    """
    subtask_key = f"{parent_task_key}-{subtask_id}"
    import json as _json

    from .schema import TASK_DIR_TEMPLATE

    data = _json.loads(_json.dumps(TASK_DIR_TEMPLATE))
    data["task_key"] = subtask_key
    data["task_number"] = subtask_id
    data["source"]["type"] = "ui"
    data["task_type"] = task_type or "subtask"
    data["flow"] = flow
    data["complexity"] = complexity or "low"
    if estimate_hours is not None:
        data["estimate_hours"] = estimate_hours
    data["research_docs"] = []
    if subtask_title:
        data["title"] = subtask_title
    return _json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def list_stages(stdir: Path) -> list[str]:
    """Return sorted stage directory names inside a subtask directory."""
    if not stdir.is_dir():
        return []
    return sorted(
        child.name
        for child in stdir.iterdir()
        if child.is_dir() and child.name.startswith("stage")
    )


def current_stage(stages: list[str]) -> str | None:
    numbered = (stage for stage in stages if stage[5:].isdecimal())
    return max(numbered, key=lambda stage: int(stage[5:]), default=None)


def list_sub_subtasks(stdir: Path) -> list[str]:
    """Return sorted sub-subtask directory names (excluding stage dirs)."""
    sub_dir = stdir / "subtasks"
    if not sub_dir.is_dir():
        return []
    return sorted(
        child.name
        for child in sub_dir.iterdir()
        if child.is_dir() and not child.name.startswith("stage")
    )
