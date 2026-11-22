"""task.json schema template and scaffold builder.

The template is draft-0.2. Semantic fields (title, intent, acceptance criteria,
owner, priority, …) are deliberately left unset so the agent/skill fills them in.

The scaffold is built as a Python dict and serialized with json.dumps() to avoid
brace-escaping problems that str.format() would have with JSON's literal { }.
"""

from __future__ import annotations

import json

TASK_DIR_TEMPLATE = {
    "schema_version": "draft-0.2",
    "task_id": None,
    "task_key": "{task_key}",
    "task_number": "{task_number}",
    "source": {
        "type": "{source_type}",
        "native_id": None,
        "provenance": "created by arch task init",
        "revision": None,
        "captured_at": None,
        "attachments": [],
        "comments": [],
        "history": [],
    },
    "title": "",
    "kind": "feature",
    "intent": "",
    "scope": {
        "in": [],
        "out": [],
        "allowed_files_modules": [],
    },
    "current_behavior": None,
    "evidence": [],
    "contracts_and_invariants": [],
    "acceptance_criteria": [],
    "target_release": "unset",
    "project_context_refs": [],
    "constraints": [],
    "assumptions": [],
    "open_questions": [],
    "risk": "low",
    "authority": {
        "allowed": [],
        "forbidden": [],
        "approval_required": [],
    },
    "approvals": [],
    "task_type": "feature",
    "flow": None,
    "complexity": "low",
    "estimate_hours": None,
    "subtasks": [],
    "depends_on": [],
    "phase": "intake",
    "rollback_plan": None,
    "implementation_plan": [],
    "related_docs": [],
    "related_tests": [],
    "research_docs": [],
    "changed_files": {
        "added": [],
        "modified": [],
        "deleted": [],
    },
    "owner": "unset",
    "priority": "unset",
    "stage_history": [],
}


def scaffold_task_json(task_key: str, task_number: str, source_type: str, source_prefix=None) -> str:
    """Build a minimal scaffold task.json with semantic fields left unset."""
    data = json.loads(json.dumps(TASK_DIR_TEMPLATE))
    data["task_key"] = task_key
    data["task_number"] = task_number
    data["source"]["type"] = source_type
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"
