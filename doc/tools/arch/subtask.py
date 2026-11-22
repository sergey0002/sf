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
    parent_task_key: str, subtask_id: str, subtask_title: str | None = None
) -> str:
    """Build a minimal scaffold task.json for a subtask under the given parent."""
    subtask_key = f"{parent_task_key}-{subtask_id}"
    data = json.loads(json.dumps(TASK_DIR_TEMPLATE)) if False else None
    # Use scaffold_task_json template then override title
    from .schema import TASK_DIR_TEMPLATE
    import json as _json
    data = _json.loads(_json.dumps(TASK_DIR_TEMPLATE))
    data["task_key"] = subtask_key
    data["task_number"] = subtask_id
    data["source"]["type"] = "ui"
    # Subtasks are leaf work items. Use scaffold type (required_fields: [],
    # subtask_policy: forbidden, allowed_flows: [minimal-scaffold]) so empty
    # subtasks list is valid and no extra type-specific fields are required.
    data["task_type"] = "scaffold"
    data["flow"] = "minimal-scaffold"
    data["research_docs"] = []
    data["complexity"] = "low"
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
