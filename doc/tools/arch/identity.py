"""Task-key derivation: numbers, sources and prefixes.

The CLI never allocates task numbers. It only validates and derives keys from
the explicit contract:

- Jira: bare four-digit number, no prefix.
- UI (user input): four-digit number with reserved ``UI-`` prefix.
- Other sources: four-digit number + explicit uppercase prefix (e.g. ``GH-``).
"""

from __future__ import annotations

from .constants import TASK_NUMBER_RE, TASK_PREFIX_RE, TASK_KEY_RE


def normalize_task_identity(
    source: str, number: str, prefix: str | None = None
) -> dict[str, str | None]:
    """Apply the explicit task-number/source-prefix contract.

    Never allocates IDs; only validates and derives from inputs.
    """
    source = source.strip().lower()
    if not source:
        raise ValueError("source must be a non-empty source identifier")
    if not TASK_NUMBER_RE.fullmatch(number):
        raise ValueError("task number must be exactly four decimal digits")
    if source == "jira":
        if prefix is not None:
            raise ValueError("Jira task keys have no source prefix")
        key, applied_prefix = number, None
    elif source == "ui":
        if prefix not in (None, "UI"):
            raise ValueError("UI (user input) tasks use the reserved UI prefix")
        key, applied_prefix = f"UI-{number}", "UI"
    else:
        if prefix is None:
            raise ValueError(f"source {source!r} requires an explicit prefix")
        prefix = prefix.strip().upper()
        if not TASK_PREFIX_RE.fullmatch(prefix):
            raise ValueError(
                "source prefix must be 1-8 uppercase letters/digits, starting with a letter"
            )
        if prefix == "UI":
            raise ValueError("UI prefix is reserved for user-input tasks")
        key, applied_prefix = f"{prefix}-{number}", prefix
    return {
        "source_type": source,
        "task_number": number,
        "source_prefix": applied_prefix,
        "task_key": key,
    }


def parse_task_key(task_key: str) -> dict[str, str | None]:
    """Parse a task_key into source_type, task_number, source_prefix.

    Never allocates a number; only validates and derives from the key itself.
    """
    match = TASK_KEY_RE.fullmatch(task_key)
    if not match:
        raise ValueError(
            f"invalid task_key {task_key!r}: expected Jira bare number (1234), "
            f"UI-<number> (UI-1234), or <PREFIX>-<number> (GH-1234)"
        )
    jira_num, ui_num, prefix, other_num = match.groups()
    if jira_num is not None:
        return {"source_type": "jira", "task_number": jira_num, "source_prefix": None}
    if ui_num is not None:
        return {"source_type": "ui", "task_number": ui_num, "source_prefix": "UI"}
    return {"source_type": "other", "task_number": other_num, "source_prefix": prefix}


def task_dir(root, task_key: str):
    """Return the canonical task directory path for a task key."""
    from pathlib import Path

    root = Path(root)
    return root / "doc" / "tasks" / task_key
