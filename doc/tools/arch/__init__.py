"""Deterministic CLI for the sample doc/architecture store.

Split into modules so the codebase stays maintainable and extensible:

- constants.py  — regexes, enums, task.json schema template
- identity.py   — task-key derivation from source, number and prefix
- task_registry.py — CLI-owned JSON task-number registry and allocation
- schema.py     — task.json scaffold
- validation.py — task.json structure validation
- store.py      — ArchitectureStore (documents, index, links, refs)
- subtask.py    — subtask directory/helpers
- cli/          — modular command-line interface (Command pattern)
- body_validation.py — document body validation by type schema

Semantic relevance and document meaning remain the agent/owner's responsibility.
"""

__version__ = "0.2.0"

from .constants import (
    FRONTMATTER,
    LINK,
    FENCE,
    TASK_NUMBER_RE,
    TASK_PREFIX_RE,
    TASK_KEY_RE,
    PATHS_CONFIG_RELATIVE,
    ALLOWED_PATHS_KEY,
    PROJECT_KEY,
    PROJECT_TASK_TYPES_KEY,
    PROJECT_PHASES_KEY,
    PROJECT_RISK_LEVELS_KEY,
    PROJECT_SOURCE_TYPES_KEY,
    PROJECT_TASK_SCHEMA_REQUIRED_FIELDS_KEY,
    TASK_CONF_TYPES_DIR,
    TASK_CONF_ID_KEY,
    TASK_CONF_ALLOWED_FLOWS_KEY,
    TASK_CONF_SUBTASK_POLICY_KEY,
    TASK_CONF_CLOSE_POLICY_KEY,
    TASK_CONF_REQUIRED_FIELDS_KEY,
    TASK_CONF_COMPLEXITY_ALLOWED_KEY,
    FLOW_RE,
    path_is_allowed,
)
from .identity import normalize_task_identity, parse_task_key, task_dir
from .schema import TASK_DIR_TEMPLATE, scaffold_task_json
from .validation import (
    validate_task_json,
    validate_paths,
    load_task_conf_types,
    load_task_conf_flows_for_type,
    load_task_conf_prompt,
    load_task_conf_flow_prompt,
    check_subtasks_closed,
)
from .store import Document, ArchitectureStore, UniqueKeyLoader
from .subtask import subtask_dir
from .body_validation import validate_document_body, get_supported_body_types

__all__ = [
    "__version__",
    "FRONTMATTER",
    "LINK",
    "FENCE",
    "TASK_NUMBER_RE",
    "TASK_PREFIX_RE",
    "TASK_KEY_RE",
    "PATHS_CONFIG_RELATIVE",
    "ALLOWED_PATHS_KEY",
    "PROJECT_KEY",
    "PROJECT_TASK_TYPES_KEY",
    "PROJECT_PHASES_KEY",
    "PROJECT_RISK_LEVELS_KEY",
    "PROJECT_SOURCE_TYPES_KEY",
    "PROJECT_TASK_SCHEMA_REQUIRED_FIELDS_KEY",
    "TASK_CONF_TYPES_DIR",
    "TASK_CONF_ID_KEY",
    "TASK_CONF_ALLOWED_FLOWS_KEY",
    "TASK_CONF_SUBTASK_POLICY_KEY",
    "TASK_CONF_CLOSE_POLICY_KEY",
    "TASK_CONF_REQUIRED_FIELDS_KEY",
    "TASK_CONF_COMPLEXITY_ALLOWED_KEY",
    "FLOW_RE",
    "path_is_allowed",
    "normalize_task_identity",
    "parse_task_key",
    "task_dir",
    "TASK_DIR_TEMPLATE",
    "scaffold_task_json",
    "validate_task_json",
    "validate_paths",
    "load_task_conf_types",
    "load_task_conf_flows_for_type",
    "load_task_conf_prompt",
    "load_task_conf_flow_prompt",
    "check_subtasks_closed",
    "validate_document_body",
    "get_supported_body_types",
    "Document",
    "ArchitectureStore",
    "UniqueKeyLoader",
    "subtask_dir",
]
