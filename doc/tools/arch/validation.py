"""task.json structure validation — fully config-driven.

All enum values, required fields, allowed flows and complexity levels are loaded
from YAML configs (doc/config/paths.yaml and doc/config/task-conf/types/*/config.yaml).
No hardcoded task_type, phase, risk, source.type or required-field list in Python.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

try:
    import yaml  # noqa: F401
except ImportError:  # pragma: no cover - exercised by CLI users
    yaml = None

from .constants import (
    TASK_NUMBER_RE,
    TASK_KEY_RE,
    FLOW_RE,
    PATHS_CONFIG_RELATIVE,
    ALLOWED_PATHS_KEY,
    PROJECT_KEY,
    STRUCTURE_RULES_KEY,
    ONLY_DECLARED_PATHS_KEY,
    ARCHITECTURE_DOC_EXTENSIONS_KEY,
    FRONTMATTER_REQUIRED_FOR_KEY,
    GENERATED_FILES_KEY,
    PROJECT_ID_FORMATS_KEY,
    PROJECT_DOCUMENT_TYPES_KEY,
    PROJECT_DOCUMENT_STATUSES_KEY,
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
    path_is_allowed,
    FRONTMATTER,
)


# ---------------------------------------------------------------------------
# task.json validation — config-driven
# ---------------------------------------------------------------------------


def _load_project_config(root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """Загрузить проектную секцию paths.yaml."""
    config, errors = load_paths_config(root)
    if errors:
        return None, errors
    project = config.get(PROJECT_KEY, {}) or {}
    if not isinstance(project, dict):
        return None, ["paths.yaml: project must be a mapping"]
    return project, errors


def _get_list(project: dict[str, Any], key: str) -> list[str]:
    value = project.get(key, [])
    return value if isinstance(value, list) else []


def _validate_array_of_strings(data: Any, field_name: str, errors: list[str]) -> None:
    """Базовая структура: поле — массив строк."""
    if data is not None:
        if not isinstance(data, list):
            errors.append(f"task.json: {field_name} must be an array")
        else:
            for i, item in enumerate(data):
                if not isinstance(item, str):
                    errors.append(f"task.json: {field_name}[{i}] must be a string")


_RELATED_DOC_ID_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:-[A-Za-z0-9]+)+$")


def _validate_subtasks(value: Any, errors: list[str]) -> None:
    """Validate the subtask array shape: id, title, status and path are required."""
    if value is None:
        return
    if not isinstance(value, list):
        errors.append("task.json: subtasks must be an array")
        return
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"task.json: subtasks[{i}] must be an object")
            continue
        for required in ("id", "title", "status", "path"):
            if required not in item:
                errors.append(
                    f"task.json: subtasks[{i}] missing required field {required!r}"
                )


def _validate_related_docs(value: Any, errors: list[str]) -> None:
    """Validate related_docs as an array of stable architecture document IDs."""
    if value is None:
        return
    if not isinstance(value, list):
        errors.append("task.json: related_docs must be an array")
        return
    for i, item in enumerate(value):
        if not isinstance(item, str):
            errors.append(f"task.json: related_docs[{i}] must be a string")
        elif not _RELATED_DOC_ID_RE.fullmatch(item):
            errors.append(
                f"task.json: related_docs[{i}] must be a stable document ID "
                f"(e.g. SYS-simple-factory), got {item!r}"
            )


def _validate_related_tests(value: Any, errors: list[str]) -> None:
    """Validate related_tests entries: each requires test_id and location."""
    if value is None:
        return
    if not isinstance(value, list):
        errors.append("task.json: related_tests must be an array")
        return
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"task.json: related_tests[{i}] must be an object")
            continue
        for required in ("test_id", "location"):
            if required not in item:
                errors.append(
                    f"task.json: related_tests[{i}] missing required field {required!r}"
                )


def _validate_stage_history(value: Any, errors: list[str]) -> None:
    """Validate stage_history entries: each requires stage_id and status."""
    if value is None:
        return
    if not isinstance(value, list):
        errors.append("task.json: stage_history must be an array")
        return
    for i, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"task.json: stage_history[{i}] must be an object")
            continue
        for required in ("stage_id", "status"):
            if required not in item:
                errors.append(
                    f"task.json: stage_history[{i}] missing required field {required!r}"
                )


def _validate_source_field(source: Any, source_types: list[str], task_key: str, errors: list[str]) -> None:
    """Валидация поля source из task.json."""
    if not isinstance(source, dict):
        errors.append("task.json: source must be an object")
        return

    st = source.get("type")
    if st is not None and source_types and st not in source_types:
        errors.append(
            f"task.json: source.type must be one of {'/'.join(source_types)}, got {st!r}"
        )

    # Jira: task_key must be bare four-digit number
    if st == "jira":
        data_key = None  # will be checked by caller
        if not TASK_NUMBER_RE.fullmatch(task_key):
            errors.append("task.json: Jira task_key must be a bare four-digit number")
    # UI: task_key must start with UI-
    if st == "ui" and not task_key.startswith("UI-"):
        errors.append("task.json: UI task_key must start with UI- prefix")

    # Source traceability arrays (optional, validated if present)
    for field_name in ("attachments", "comments", "history"):
        value = source.get(field_name)
        if value is not None and not isinstance(value, list):
            errors.append(f"task.json: source.{field_name} must be an array")


def _validate_research_docs(
    research_docs: Any, task_key: str, errors: list[str]
) -> None:
    """Валидация массива research_docs."""
    if research_docs is None:
        return
    if not isinstance(research_docs, list):
        errors.append("task.json: research_docs must be an array")
        return
    expected_prefix = f"doc/tasks/{task_key}/research/"
    for i, rd in enumerate(research_docs):
        if not isinstance(rd, dict):
            errors.append(f"task.json: research_docs[{i}] must be an object")
            continue
        for req in ("id", "title", "path", "source_type", "source_ref", "summary", "status"):
            if req not in rd:
                errors.append(
                    f"task.json: research_docs[{i}] missing required field {req!r}"
                )
        st = rd.get("source_type")
        if st is not None and st not in ("web", "code", "internal"):
            errors.append(
                f"task.json: research_docs[{i}].source_type must be web/code/internal, got {st!r}"
            )
        st = rd.get("status")
        if st is not None and st not in ("hypothesis", "confirmed", "rejected", "archived"):
            errors.append(
                f"task.json: research_docs[{i}].status must be hypothesis/confirmed/rejected/archived, got {st!r}"
            )
        path = rd.get("path")
        if path is not None and not isinstance(path, str):
            errors.append(f"task.json: research_docs[{i}].path must be a string")
        elif path is not None:
            if not path.startswith(expected_prefix) or not path.endswith(".md"):
                errors.append(
                    f"task.json: research_docs[{i}].path must be under {expected_prefix} and end with .md, got {path!r}"
                )


def _validate_task_type_vs_flow(
    root: Path, task_type: str, flow: str, errors: list[str]
) -> None:
    """Проверяет, что поток flow разрешён для типа задачи task_type по task-conf."""
    types, terrors = load_task_conf_types(root)
    if terrors:
        for e in terrors:
            errors.append(e)
        return
    if task_type not in types:
        return  # type config may not exist yet; not a hard error
    type_conf = types[task_type]
    allowed_flows = type_conf.get(TASK_CONF_ALLOWED_FLOWS_KEY, [])
    if flow not in allowed_flows:
        errors.append(
            f"task.json: flow {flow!r} not allowed for task_type {task_type!r}; "
            f"allowed: {', '.join(allowed_flows) or 'none'}"
        )


def validate_task_json(data: dict[str, Any], task_key: str, root: Path | None = None) -> list[str]:
    """Validate a parsed task.json structure. Returns list of error messages.

    All rules are loaded from YAML configs:
      - doc/config/paths.yaml (project section): task_types, phases, risk_levels,
        source_types, task_schema_required_fields
      - doc/config/task-conf/types/<type>/config.yaml: required_fields,
        allowed_flows, complexity_allowed, subtask_policy, close_policy
    """
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["task.json is not a JSON object"]

    # --- Load project config -------------------------------------------------
    project, proj_errors = _load_project_config(root) if root else (None, [])
    # A missing/broken project config is an error, but structural field checks
    # must still run so the caller gets actionable field-level diagnostics.
    errors.extend(proj_errors)
    if project is None:
        project = {}

    task_types = _get_list(project, PROJECT_TASK_TYPES_KEY)
    phases = _get_list(project, PROJECT_PHASES_KEY)
    risk_levels = _get_list(project, PROJECT_RISK_LEVELS_KEY)
    source_types = _get_list(project, PROJECT_SOURCE_TYPES_KEY)
    base_required_fields = _get_list(
        project, PROJECT_TASK_SCHEMA_REQUIRED_FIELDS_KEY
    )

    # --- Load task type config ----------------------------------------------
    type_conf: dict[str, Any] = {}
    task_type = data.get("task_type")
    if task_type and root:
        types, terrors = load_task_conf_types(root)
        if terrors:
            for e in terrors:
                errors.append(e)
        if task_type in types:
            type_conf = types[task_type]

    # --- Required fields: base (paths.yaml) + type-specific (task-conf) -----
    type_required = type_conf.get(TASK_CONF_REQUIRED_FIELDS_KEY, [])
    if not isinstance(type_required, list):
        type_required = []
    all_required = list(dict.fromkeys(base_required_fields + type_required))

    for field in all_required:
        if field not in data:
            errors.append(f"task.json: missing required field {field!r}")

    # --- task_number ---------------------------------------------------------
    task_number = data.get("task_number")
    if not isinstance(task_number, str) or not TASK_NUMBER_RE.fullmatch(task_number):
        errors.append(
            f"task.json: task_number must be exactly four decimal digits, got {task_number!r}"
        )

    # --- task_key ------------------------------------------------------------
    data_key = data.get("task_key")
    if data_key != task_key:
        errors.append(f"task.json: task_key {data_key!r} does not match directory {task_key!r}")

    # --- source --------------------------------------------------------------
    source = data.get("source")
    _validate_source_field(source, source_types, task_key, errors)

    # --- task_type enum ------------------------------------------------------
    if task_type is not None:
        if not isinstance(task_type, str):
            errors.append("task.json: task_type must be a string")
        elif task_types and task_type not in task_types:
            errors.append(
                f"task.json: task_type must be one of {'/'.join(task_types)}, got {task_type!r}"
            )

    # --- phase enum ----------------------------------------------------------
    phase = data.get("phase")
    if phase is not None:
        if not isinstance(phase, str):
            errors.append("task.json: phase must be a string")
        elif phases and phase not in phases:
            errors.append(
                f"task.json: phase must be one of {'/'.join(phases)}, got {phase!r}"
            )

    # --- risk enum -----------------------------------------------------------
    risk = data.get("risk")
    if risk is not None:
        if not isinstance(risk, str):
            errors.append("task.json: risk must be a string")
        elif risk_levels and risk not in risk_levels:
            errors.append(
                f"task.json: risk must be one of {'/'.join(risk_levels)}, got {risk!r}"
            )

    # --- flow (поток) --------------------------------------------------------
    flow = data.get("flow")
    if flow is not None:
        if not isinstance(flow, str) or not FLOW_RE.fullmatch(flow):
            errors.append(
                f"task.json: flow must be a lowercase slug (a-z, 0-9, -), got {flow!r}"
            )
        elif task_type and root:
            _validate_task_type_vs_flow(root, task_type, flow, errors)

    # --- complexity ----------------------------------------------------------
    complexity = data.get("complexity")
    if complexity is not None:
        complexity_allowed = type_conf.get(TASK_CONF_COMPLEXITY_ALLOWED_KEY, [])
        if not isinstance(complexity, str):
            errors.append("task.json: complexity must be a string")
        elif complexity_allowed and complexity not in complexity_allowed:
            errors.append(
                f"task.json: complexity must be one of {'/'.join(complexity_allowed)}, got {complexity!r}"
            )

    # --- subtask_policy ------------------------------------------------------
    subtask_policy = type_conf.get(TASK_CONF_SUBTASK_POLICY_KEY)
    subtasks = data.get("subtasks")
    if subtask_policy is not None:
        if subtask_policy == "required":
            if not isinstance(subtasks, list) or len(subtasks) == 0:
                errors.append(
                    f"task.json: subtask_policy is 'required' but subtasks is empty or missing"
                )
        elif subtask_policy == "forbidden":
            if isinstance(subtasks, list) and len(subtasks) > 0:
                errors.append(
                    f"task.json: subtask_policy is 'forbidden' but subtasks is not empty"
                )

    # --- Structural checks for object fields --------------------------------
    scope = data.get("scope")
    if scope is not None:
        if not isinstance(scope, dict):
            errors.append("task.json: scope must be an object")
        else:
            for side in ("in", "out"):
                v = scope.get(side)
                if v is not None and not isinstance(v, list):
                    errors.append(f"task.json: scope.{side} must be an array")

    changed_files = data.get("changed_files")
    if changed_files is not None:
        if not isinstance(changed_files, dict):
            errors.append("task.json: changed_files must be an object")
        else:
            for side in ("added", "modified", "deleted"):
                v = changed_files.get(side)
                if v is not None and not isinstance(v, list):
                    errors.append(f"task.json: changed_files.{side} must be an array")

    authority = data.get("authority")
    if authority is not None:
        if not isinstance(authority, dict):
            errors.append("task.json: authority must be an object")
        else:
            for side in ("allowed", "forbidden", "approval_required"):
                v = authority.get(side)
                if v is not None and not isinstance(v, list):
                    errors.append(f"task.json: authority.{side} must be an array")

    _validate_subtasks(data.get("subtasks"), errors)
    _validate_related_docs(data.get("related_docs"), errors)
    _validate_related_tests(data.get("related_tests"), errors)
    _validate_stage_history(data.get("stage_history"), errors)

    # --- Simple string fields (if present) -----------------------------------
    simple_string_fields = ("task_id", "kind", "current_behavior", "rollback_plan", "owner", "priority")
    for field_name in simple_string_fields:
        value = data.get(field_name)
        if value is not None and not isinstance(value, str):
            errors.append(f"task.json: {field_name} must be a string")

    # --- Simple array-of-strings fields --------------------------------------
    array_string_fields = ("depends_on", "evidence", "contracts_and_invariants",
                           "allowed_files_modules")
    for field_name in array_string_fields:
        _validate_array_of_strings(data.get(field_name), field_name, errors)

    # --- research_docs (special validation with path prefix) -----------------
    _validate_research_docs(data.get("research_docs"), task_key, errors)

    return errors


# ---------------------------------------------------------------------------
# Task-conf loading (doc/config/task-conf/) — иерархическая структура
# ---------------------------------------------------------------------------


def load_task_conf_types(root: Path) -> tuple[dict[str, Any], list[str]]:
    """Загрузить все конфиги типов задач из doc/config/task-conf/types/*/config.yaml.

    Каждый тип — папка с config.yaml и prompt.md, внутри подпапка flows/.
    Возвращает словарь {type_id: conf} где conf включает поле flows со списком
    конфигов потоков этого типа.
    """
    types_dir = root / TASK_CONF_TYPES_DIR
    errors: list[str] = []
    types: dict[str, Any] = {}
    if not types_dir.is_dir():
        return types, [f"Task-conf types dir not found: {types_dir.relative_to(root)}"]
    if yaml is None:
        return types, ["PyYAML is not installed; cannot read task-conf types"]
    for type_dir in sorted(types_dir.iterdir()):
        if not type_dir.is_dir():
            continue
        config_path = type_dir / "config.yaml"
        if not config_path.exists():
            continue
        try:
            conf = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            errors.append(f"Invalid YAML in {config_path.relative_to(root)}: {exc}")
            continue
        if not isinstance(conf, dict) or not conf.get(TASK_CONF_ID_KEY):
            continue
        type_id = conf[TASK_CONF_ID_KEY]
        # Загружаем потоки этого типа из подпапки flows/
        flows_dir = type_dir / "flows"
        type_flows: dict[str, Any] = {}
        if flows_dir.is_dir():
            for flow_dir in sorted(flows_dir.iterdir()):
                if not flow_dir.is_dir():
                    continue
                flow_config_path = flow_dir / "config.yaml"
                if not flow_config_path.exists():
                    continue
                try:
                    flow_conf = yaml.safe_load(
                        flow_config_path.read_text(encoding="utf-8")
                    )
                except yaml.YAMLError as exc:
                    errors.append(
                        f"Invalid YAML in {flow_config_path.relative_to(root)}: {exc}"
                    )
                    continue
                if isinstance(flow_conf, dict) and flow_conf.get(TASK_CONF_ID_KEY):
                    type_flows[flow_conf[TASK_CONF_ID_KEY]] = flow_conf
        conf["flows"] = type_flows
        types[type_id] = conf
    return types, errors


def load_task_conf_flows_for_type(
    root: Path, type_id: str
) -> tuple[dict[str, Any], list[str]]:
    """Загрузить конфиги потоков для конкретного типа задач.

    Возвращает (flows, errors) где flows — словарь {flow_id: conf}.
    """
    types, errors = load_task_conf_types(root)
    if errors:
        return {}, errors
    if type_id not in types:
        return {}, [f"Task type {type_id!r} not found in task-conf"]
    return types[type_id].get("flows", {}), errors


def load_task_conf_prompt(root: Path, type_id: str) -> tuple[str | None, list[str]]:
    """Загрузить стартовый промпт типа задачи из doc/config/task-conf/types/<type>/prompt.md."""
    prompt_path = root / TASK_CONF_TYPES_DIR / type_id / "prompt.md"
    errors: list[str] = []
    if not prompt_path.exists():
        return None, [f"Prompt not found: {prompt_path.relative_to(root)}"]
    try:
        content = prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [f"Cannot read prompt {prompt_path.relative_to(root)}: {exc}"]
    return content, errors


def load_task_conf_flow_prompt(
    root: Path, type_id: str, flow_id: str
) -> tuple[str | None, list[str]]:
    """Загрузить стартовый промпт потока из
    doc/config/task-conf/types/<type>/flows/<flow>/prompt.md."""
    prompt_path = (
        root / TASK_CONF_TYPES_DIR / type_id / "flows" / flow_id / "prompt.md"
    )
    errors: list[str] = []
    if not prompt_path.exists():
        return None, [f"Flow prompt not found: {prompt_path.relative_to(root)}"]
    try:
        content = prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [f"Cannot read flow prompt {prompt_path.relative_to(root)}: {exc}"]
    return content, errors


# ---------------------------------------------------------------------------
# Subtask closure policy check
# ---------------------------------------------------------------------------


def check_subtasks_closed(root: Path, task_key: str) -> tuple[bool, list[str]]:
    """Проверяет, закрыты ли все подзадачи задачи.

    Возвращает (all_closed, errors). Если close_policy требует all_subtasks_required
    и есть открытые/незавершённые подзадачи — возвращает False со списком ошибок.
    """
    from .identity import task_dir

    root = Path(root)
    tdir = task_dir(root, task_key)
    if not tdir.is_dir():
        return False, [f"Task directory not found: {tdir.relative_to(root)}"]

    subtasks_dir = tdir / "subtasks"
    if not subtasks_dir.is_dir():
        return True, []  # нет подзадач — считаем закрытым

    errors: list[str] = []
    all_closed = True
    for st_dir in sorted(subtasks_dir.iterdir()):
        if not st_dir.is_dir():
            continue
        st_json = st_dir / "task.json"
        if not st_json.exists():
            errors.append(f"Subtask {st_dir.name}: task.json missing")
            all_closed = False
            continue
        try:
            data = json.loads(st_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"Subtask {st_dir.name}: invalid JSON: {exc}")
            all_closed = False
            continue
        phase = data.get("phase", "")
        if phase != "completed":
            all_closed = False
            errors.append(
                f"Subtask {st_dir.name}: phase is {phase!r}, not completed"
            )
    return all_closed, errors


# ---------------------------------------------------------------------------
# Path validation (doc/config/paths.yaml enforcement)
# ---------------------------------------------------------------------------


def load_paths_config(root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    """Load doc/config/paths.yaml. Returns (config, errors)."""
    config_path = root / PATHS_CONFIG_RELATIVE
    errors: list[str] = []
    if not config_path.exists():
        return None, [f"Paths config not found: {config_path.relative_to(root)}"]
    if yaml is None:
        return None, ["PyYAML is not installed; cannot read paths.yaml"]
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return None, [f"Paths config invalid YAML: {exc}"]
    if not isinstance(config, dict):
        return None, ["Paths config is not a YAML mapping"]
    return config, errors


def validate_paths(root: Path) -> list[str]:
    """Validate doc/ against declared paths in paths.yaml.

    Returns list of human-readable error messages (empty when valid).
    Checks:
      - every file under doc/ matches at least one allowed path pattern;
      - every declared path pattern has at least one matching file (unless template-only);
      - .md files under doc/architecture/ have valid frontmatter with required fields.
    """
    errors: list[str] = []

    config, config_errors = load_paths_config(root)
    if config_errors:
        return config_errors

    allowed_paths = config.get(ALLOWED_PATHS_KEY, [])
    if not isinstance(allowed_paths, list):
        errors.append("paths.yaml: allowed_paths must be a list")
        return errors

    structure_rules = config.get(STRUCTURE_RULES_KEY, {}) or {}
    only_declared = structure_rules.get(ONLY_DECLARED_PATHS_KEY, True)
    arch_extensions = structure_rules.get(ARCHITECTURE_DOC_EXTENSIONS_KEY, [".md", ".json"])
    frontmatter_required = structure_rules.get(FRONTMATTER_REQUIRED_FOR_KEY, [])
    generated_files = structure_rules.get(GENERATED_FILES_KEY, []) or []

    doc_root = root / "doc"
    if not doc_root.is_dir():
        return [f"doc/ directory not found: {doc_root.relative_to(root)}"]

    # Collect all actual files under doc/ (excluding caches)
    actual_files: list[str] = []
    for path in doc_root.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts and ".pytest_cache" not in path.parts:
            rel = str(path.relative_to(root))
            actual_files.append(rel)

    # 1. Every actual file must be allowed
    for rel in sorted(actual_files):
        if not path_is_allowed(rel, allowed_paths):
            errors.append(
                f"Undeclared path in doc/: {rel} — not listed in {PATHS_CONFIG_RELATIVE} allowed_paths"
            )

    # 2. Declared paths that are exact (no { }) should exist on disk
    for pattern in allowed_paths:
        if "{" not in pattern:
            full = root / pattern
            if not full.exists():
                errors.append(
                    f"Declared path missing on disk: {pattern} — expected by {PATHS_CONFIG_RELATIVE}"
                )

    # 3. Frontmatter required for architecture .md files
    import fnmatch

    arch_md_files = [
        rel for rel in actual_files
        if rel.startswith("doc/architecture/") and rel.endswith(".md")
    ]
    for rel in sorted(arch_md_files):
        if not any(fnmatch.fnmatch(rel, pat) for pat in frontmatter_required):
            continue
        full = root / rel
        try:
            content = full.read_text(encoding="utf-8")
        except OSError as exc:
            errors.append(f"Cannot read {rel}: {exc}")
            continue
        m = FRONTMATTER.match(content)
        if not m:
            errors.append(f"Missing or invalid YAML frontmatter: {rel}")
            continue
        try:
            front = yaml.safe_load(m.group(1)) if yaml else {}
        except yaml.YAMLError as exc:
            errors.append(f"Invalid YAML frontmatter in {rel}: {exc}")
            continue
        if not isinstance(front, dict):
            errors.append(f"Frontmatter is not a mapping: {rel}")
            continue
        for required in ("id", "type", "title", "summary", "status"):
            if required not in front:
                errors.append(f"Frontmatter missing required field {required!r}: {rel}")
        ftype = front.get("type")
        project = config.get(PROJECT_KEY, {}) or {}
        doc_types = project.get(PROJECT_DOCUMENT_TYPES_KEY, [])
        if ftype and doc_types and ftype not in doc_types:
            errors.append(f"Unknown document type {ftype!r}: {rel}")
        fstatus = front.get("status")
        doc_statuses = project.get(PROJECT_DOCUMENT_STATUSES_KEY, [])
        if fstatus and doc_statuses and fstatus not in doc_statuses:
            errors.append(f"Unknown document status {fstatus!r}: {rel}")

    return errors
