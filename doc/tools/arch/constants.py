"""Constants, regexes and key names shared across the arch CLI package.

All enum values, required fields and allowed lists are loaded from YAML configs
(doc/config/paths.yaml and doc/config/task-conf/types/*/config.yaml) — there is
no hardcoded task_type, phase, risk, source.type or required-field list in Python.
"""

from __future__ import annotations

import re

# --- Frontmatter / link parsing ------------------------------------------------

FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
LINK = re.compile(
    r"\[[^\]]*\]\((<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)"
)
FENCE = re.compile(r"^\s*(```+|~~~+)")

# --- Task identity contract ----------------------------------------------------

# Four-digit task number (e.g. 0427, 0001). Never allocated automatically.
TASK_NUMBER_RE = re.compile(r"^[0-9]{4}$")

# Source prefix: 1-8 uppercase letters/digits, starting with a letter.
TASK_PREFIX_RE = re.compile(r"^[A-Z][A-Z0-9]{0,7}$")

# task_key: Jira bare number (1234), UI-<number> (UI-1234), or <PREFIX>-<number> (GH-1234).
TASK_KEY_RE = re.compile(
    r"^(?:([0-9]{4})|UI-([0-9]{4})|([A-Z][A-Z0-9]{0,7})-([0-9]{4}))$"
)

# --- Paths config (doc/config/paths.yaml) --------------------------------------

PATHS_CONFIG_RELATIVE = "doc/config/paths.yaml"

# Keys inside paths.yaml
ALLOWED_PATHS_KEY = "allowed_paths"
PROJECT_KEY = "project"
STRUCTURE_RULES_KEY = "structure_rules"
ONLY_DECLARED_PATHS_KEY = "only_declared_paths"
ARCHITECTURE_DOC_EXTENSIONS_KEY = "architecture_doc_extensions"
FRONTMATTER_REQUIRED_FOR_KEY = "frontmatter_required_for"
GENERATED_FILES_KEY = "generated_files"

# Project sub-keys inside paths.yaml
PROJECT_ID_FORMATS_KEY = "id_formats"
PROJECT_DOCUMENT_TYPES_KEY = "document_types"
PROJECT_DOCUMENT_STATUSES_KEY = "document_statuses"
PROJECT_TASK_TYPES_KEY = "task_types"
PROJECT_PHASES_KEY = "phases"
PROJECT_RISK_LEVELS_KEY = "risk_levels"
PROJECT_SOURCE_TYPES_KEY = "source_types"
PROJECT_TASK_SCHEMA_REQUIRED_FIELDS_KEY = "task_schema_required_fields"

# --- Task-conf (doc/config/task-conf/) -----------------------------------------

TASK_CONF_DIR = "doc/config/task-conf"
TASK_CONF_TYPES_DIR = "doc/config/task-conf/types"
TASK_CONF_FLOWS_DIR = "doc/config/task-conf/flows"

# Task-conf config keys
TASK_CONF_ID_KEY = "id"
TASK_CONF_ALLOWED_FLOWS_KEY = "allowed_flows"
TASK_CONF_DEFAULT_FLOW_KEY = "default_flow"
TASK_CONF_SUBTASK_POLICY_KEY = "subtask_policy"
TASK_CONF_CLOSE_POLICY_KEY = "close_policy"
TASK_CONF_REQUIRED_FIELDS_KEY = "required_fields"
TASK_CONF_COMPLEXITY_ALLOWED_KEY = "complexity_allowed"
TASK_CONF_COMPLEXITY_DEFAULT_KEY = "complexity_default"
TASK_CONF_FORBIDDEN_IN_SCOPE_KEY = "forbidden_in_scope"

# Task lifecycle / flow fields
FLOW_RE = re.compile(r"^[a-z][a-z0-9-]{1,63}$")


def _glob_match(pattern: str, path: str) -> bool:
    """Простое соответствие пути шаблону с фигурными скобками (без regex).

    Поддерживает одинарный сегмент {name} и glob ** для любых вложенных каталогов.
    Пример: "doc/tasks/{task_key}/task.json" соответствует "doc/tasks/UI-0001/task.json".
    """
    import fnmatch

    # Экранируем всё кроме фигурных скобок и **
    regex_parts = []
    i = 0
    while i < len(pattern):
        if pattern[i : i + 2] == "**":
            regex_parts.append(".*")
            i += 2
        elif pattern[i] == "{":
            j = pattern.find("}", i)
            if j == -1:
                regex_parts.append(re.escape(pattern[i]))
                i += 1
            else:
                regex_parts.append(r"[^/]+")
                i = j + 1
        else:
            regex_parts.append(re.escape(pattern[i]))
            i += 1
    regex = "^" + "".join(regex_parts) + "$"
    return bool(re.fullmatch(regex, path))


def path_is_allowed(relative_path: str, allowed_paths: list[str]) -> bool:
    """Проверяет, разрешён ли путь по декларированным шаблонам paths.yaml."""
    for pattern in allowed_paths:
        if _glob_match(pattern, relative_path):
            return True
    return False
