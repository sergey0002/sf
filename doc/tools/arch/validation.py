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

from .acceptance import CASE_COVERAGE, acceptance_state, criterion_ids

try:
    import yaml  # noqa: F401
except ImportError:  # pragma: no cover - exercised by CLI users
    yaml = None

from .constants import (
    TASK_NUMBER_RE,
    TASK_KEY_RE,
    FLOW_RE,
    BRANCH_RE,
    ONLY_DECLARED_PATHS_KEY,
    FRONTMATTER_REQUIRED_FOR_KEY,
    PROJECT_DOCUMENT_TYPES_KEY,
    PROJECT_DOCUMENT_STATUSES_KEY,
    PROJECT_TASK_TYPES_KEY,
    PROJECT_PHASES_KEY,
    PROJECT_RISK_LEVELS_KEY,
    PROJECT_SOURCE_TYPES_KEY,
    PROJECT_TASK_SCHEMA_REQUIRED_FIELDS_KEY,
    PROJECT_TASK_STATUSES_KEY,
    PROJECT_RELEASE_KEY,
    ROOT_TASK_CONF_KEY,
    ROOT_TASKS_KEY,
    TASK_CONF_ID_KEY,
    TASK_CONF_ALLOWED_FLOWS_KEY,
    TASK_CONF_SUBTASK_POLICY_KEY,
    TASK_CONF_CLOSE_POLICY_KEY,
    TASK_CONF_REQUIRED_FIELDS_KEY,
    TASK_CONF_COMPLEXITY_ALLOWED_KEY,
    path_is_allowed,
    FRONTMATTER,
)
from .project_config import DEFAULT_ROOTS, ProjectConfig, load_project_config
from .subtask import current_stage, list_stages
from typing import Union


ProjectConfigOrPath = Union[ProjectConfig, Path]


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
        depends_on = item.get("depends_on")
        if depends_on is not None:
            if not isinstance(depends_on, list):
                errors.append(f"task.json: subtasks[{i}].depends_on must be an array")
            else:
                for j, dep in enumerate(depends_on):
                    if not isinstance(dep, str) or not TASK_NUMBER_RE.fullmatch(dep):
                        errors.append(
                            f"task.json: subtasks[{i}].depends_on[{j}] must be a four-digit subtask id"
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
    research_docs: Any, task_key: str, errors: list[str], project_config: ProjectConfig | None,
) -> None:
    """Валидация массива research_docs."""
    if research_docs is None:
        return
    if not isinstance(research_docs, list):
        errors.append("task.json: research_docs must be an array")
        return
    tasks_path = (project_config.tasks_root.relative_to(project_config.root).as_posix()
                  if project_config else DEFAULT_ROOTS[ROOT_TASKS_KEY])
    expected_prefix = f"{tasks_path}/{task_key}/research/"
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
            if (not path.startswith(expected_prefix) or not path.endswith(".md")
                    or ".." in Path(path).parts):
                errors.append(
                    f"task.json: research_docs[{i}].path must be under {expected_prefix} and end with .md, got {path!r}"
                )


def validate_task_json(data: dict[str, Any], task_key: str, project_config: ProjectConfigOrPath | None = None) -> list[str]:
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
    if "acceptance_policy" in data:
        if data["acceptance_policy"] != CASE_COVERAGE:
            errors.append(f"task.json: acceptance_policy must be {CASE_COVERAGE!r}")
        else:
            try:
                criterion_ids(data)
            except ValueError as exc:
                errors.append(f"task.json: {exc}")

    # --- Load project config -------------------------------------------------
    if isinstance(project_config, Path):
        project_config, config_errors = load_project_config(project_config)
        errors.extend(config_errors)
    project = project_config.get_project_section() if project_config else {}

    task_types = _get_list(project, PROJECT_TASK_TYPES_KEY)
    phases = _get_list(project, PROJECT_PHASES_KEY)
    risk_levels = _get_list(project, PROJECT_RISK_LEVELS_KEY)
    source_types = _get_list(project, PROJECT_SOURCE_TYPES_KEY)
    task_statuses = _get_list(project, PROJECT_TASK_STATUSES_KEY)
    base_required_fields = _get_list(
        project, PROJECT_TASK_SCHEMA_REQUIRED_FIELDS_KEY
    )

    # --- Load task type config ----------------------------------------------
    type_conf: dict[str, Any] = {}
    task_type = data.get("task_type")
    if isinstance(task_type, str) and task_type and project_config:
        types, type_errors = load_task_conf_types(project_config)
        errors.extend(type_errors)
        type_conf = types.get(task_type, {})

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

    # --- status enum (исполнительный статус, отдельно от phase) --------------
    status = data.get("status")
    if status is not None:
        if not isinstance(status, str):
            errors.append("task.json: status must be a string")
        elif task_statuses and status not in task_statuses:
            errors.append(
                f"task.json: status must be one of {'/'.join(task_statuses)}, got {status!r}"
            )

    # --- release config --------------------------------------------------------
    release = project.get(PROJECT_RELEASE_KEY, {}) if isinstance(project, dict) else {}
    if not isinstance(release, dict):
        release = {}
    default_branch = release.get("default_branch", "main")
    # Enforcement is opt-in: the branch contract belongs to UI-0027 and must not
    # block the existing corpus until the migration is explicitly enabled.
    enforce_branches = release.get("enforce", False) is True

    # --- target_release (обязательное при enforce) -----------------------------
    target_release = data.get("target_release")
    if enforce_branches and (not isinstance(target_release, str) or target_release == "unset"):
        errors.append("task.json: target_release must be set (not 'unset')")

    # --- branch (рабочая ветка задачи) ----------------------------------------
    branch = data.get("branch")
    if branch in (None, "unset"):
        if enforce_branches:
            errors.append("task.json: branch must be set (not 'unset')")
    elif not isinstance(branch, str):
        errors.append("task.json: branch must be a string")
    elif not BRANCH_RE.fullmatch(branch):
        errors.append(f"task.json: branch must be a valid git branch name, got {branch!r}")

    # --- release_branch (ветка для мерджа) ------------------------------------
    release_branch = data.get("release_branch")
    if release_branch in (None, "unset"):
        if enforce_branches:
            errors.append("task.json: release_branch must be set (not 'unset')")
    elif not isinstance(release_branch, str):
        errors.append("task.json: release_branch must be a string")
    elif not BRANCH_RE.fullmatch(release_branch):
        errors.append(f"task.json: release_branch must be a valid git branch name, got {release_branch!r}")

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
        elif type_conf:
            allowed_flows = type_conf.get(TASK_CONF_ALLOWED_FLOWS_KEY, [])
            if flow not in allowed_flows:
                errors.append(
                    f"task.json: flow {flow!r} not allowed for task_type {task_type!r}; "
                    f"allowed: {', '.join(allowed_flows) or 'none'}"
                )

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

    # --- estimate_hours ------------------------------------------------------
    estimate_hours = data.get("estimate_hours")
    if estimate_hours is not None:
        if (isinstance(estimate_hours, bool)
                or not isinstance(estimate_hours, (int, float))
                or estimate_hours <= 0):
            errors.append(
                f"task.json: estimate_hours must be a positive number of hours, got {estimate_hours!r}"
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
            planned = scope.get("write_files")
            if planned is not None and (
                not isinstance(planned, list)
                or any(not isinstance(item, str) for item in planned)
            ):
                errors.append("task.json: scope.write_files must be an array of strings")

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
    _validate_research_docs(data.get("research_docs"), task_key, errors, project_config)

    return errors


# ---------------------------------------------------------------------------
# Task-conf loading (doc/config/task-conf/) — иерархическая структура
# ---------------------------------------------------------------------------


def _task_conf_location(config: ProjectConfigOrPath) -> tuple[Path, Path]:
    if isinstance(config, ProjectConfig):
        return config.root, config.task_conf_root / "types"
    return config, config / DEFAULT_ROOTS[ROOT_TASK_CONF_KEY] / "types"


def load_task_conf_types(config: ProjectConfigOrPath) -> tuple[dict[str, Any], list[str]]:
    """Загрузить все конфиги типов задач из doc/config/task-conf/types/*/config.yaml.

    Каждый тип — папка с config.yaml и prompt.md, внутри подпапка flows/.
    Возвращает словарь {type_id: conf} где conf включает поле flows со списком
    конфигов потоков этого типа.
    """
    root, types_dir = _task_conf_location(config)
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
    config: ProjectConfigOrPath, type_id: str
) -> tuple[dict[str, Any], list[str]]:
    """Загрузить конфиги потоков для конкретного типа задач.

    Возвращает (flows, errors) где flows — словарь {flow_id: conf}.
    """
    types, errors = load_task_conf_types(config)
    if errors:
        return {}, errors
    if type_id not in types:
        return {}, [f"Task type {type_id!r} not found in task-conf"]
    return types[type_id].get("flows", {}), errors


def load_task_conf_prompt(config: ProjectConfigOrPath, type_id: str) -> tuple[str | None, list[str]]:
    """Загрузить стартовый промпт типа задачи из doc/config/task-conf/types/<type>/prompt.md."""
    root, types_dir = _task_conf_location(config)
    prompt_path = types_dir / type_id / "prompt.md"
    errors: list[str] = []
    if not prompt_path.exists():
        return None, [f"Prompt not found: {prompt_path.relative_to(root)}"]
    try:
        content = prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [f"Cannot read prompt {prompt_path.relative_to(root)}: {exc}"]
    return content, errors


def load_task_conf_flow_prompt(
    config: ProjectConfigOrPath, type_id: str, flow_id: str
) -> tuple[str | None, list[str]]:
    """Загрузить стартовый промпт потока из
    doc/config/task-conf/types/<type>/flows/<flow>/prompt.md."""
    root, types_dir = _task_conf_location(config)
    prompt_path = types_dir / type_id / "flows" / flow_id / "prompt.md"
    errors: list[str] = []
    if not prompt_path.exists():
        return None, [f"Flow prompt not found: {prompt_path.relative_to(root)}"]
    try:
        content = prompt_path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [f"Cannot read flow prompt {prompt_path.relative_to(root)}: {exc}"]
    return content, errors


def flow_prompt_steps(flow: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate ordered step IDs before resolving any prompt file."""
    steps = flow.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ValueError("flow steps must be a non-empty array")
    seen = set()
    for step in steps:
        step_id = step.get("id") if isinstance(step, dict) else None
        if not isinstance(step_id, str) or not re.fullmatch(r"[a-z][a-z0-9-]*", step_id):
            raise ValueError(f"invalid flow step ID: {step_id!r}")
        if step_id in seen:
            raise ValueError(f"duplicate flow step ID: {step_id}")
        seen.add(step_id)
    return steps


def flow_step_path(config: ProjectConfig, type_id: str, flow_id: str, step_id: str) -> Path:
    folder = config.task_conf_root / "types" / type_id / "flows" / flow_id
    path = folder / "stepsprompt" / f"{step_id}.md"
    resolved_folder = folder.resolve()
    if not resolved_folder.is_relative_to(config.task_conf_root) or not path.resolve().is_relative_to(resolved_folder):
        raise ValueError(f"step prompt escapes configured flow directory: {step_id}")
    return path


def load_task_conf_step_prompt(
    config: ProjectConfig, type_id: str, flow_id: str, step_id: str,
) -> tuple[str | None, list[str]]:
    """Read an override or the selected numbered item of the legacy prompt."""
    path = flow_step_path(config, type_id, flow_id, step_id)
    if path.exists() or path.is_symlink():
        try:
            prompt = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            return None, [f"Cannot read step prompt {path.relative_to(config.root)}: {exc}"]
        if not prompt.strip():
            return None, [f"Empty step prompt: {path.relative_to(config.root)}"]
        return prompt, []

    prompt, errors = load_task_conf_flow_prompt(config, type_id, flow_id)
    if errors:
        return None, errors
    lines = (prompt or "").splitlines()
    for i, line in enumerate(lines):
        match = re.match(r"^[0-9]+\. `([^`]+)`", line)
        if not match or match[1] != step_id:
            continue
        end = i + 1
        while end < len(lines) and (not lines[end].strip() or lines[end].startswith((" ", "\t"))):
            end += 1
        return "\n".join(lines[i:end]).rstrip() + "\n", []
    return None, [f"No prompt for step {step_id!r} in flow {flow_id!r}"]


# ---------------------------------------------------------------------------
# Subtask closure policy check
# ---------------------------------------------------------------------------


def inspect_subtasks(
    tdir: Path, task: dict[str, Any], *, project_root: Path | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return the same immediate-child facts for diagnosis and closure.

    The result includes each child's declared dependencies, readiness and the
    blocking reasons. Only immediate children are inspected.
    """
    records = task.get("subtasks", [])
    blockers: list[str] = []
    declared: dict[str, dict[str, Any]] = {}
    if not isinstance(records, list):
        blockers.append("task.json: subtasks must be an array")
        records = []
    for record in records:
        sub_id = record.get("id") if isinstance(record, dict) else None
        if not isinstance(sub_id, str) or not TASK_NUMBER_RE.fullmatch(sub_id):
            blockers.append("Declared subtask must have a four-digit id")
        elif sub_id in declared:
            blockers.append(f"Declared subtask {sub_id}: duplicate id")
        else:
            declared[sub_id] = record

    subdir = tdir / "subtasks"
    disk = {p.name: p for p in subdir.iterdir() if p.is_dir()} if subdir.is_dir() else {}
    rows: list[dict[str, Any]] = []
    by_id: dict[str, dict[str, Any]] = {}
    for sub_id in sorted(declared.keys() | disk.keys()):
        record = declared.get(sub_id)
        folder = disk.get(sub_id)
        row: dict[str, Any] = {
            "id": sub_id, "subtask_id": sub_id, "title": "", "phase": "missing",
            "declared": record is not None, "on_disk": folder is not None,
            "depends_on": [], "ready": False, "readiness": "blocked",
        }
        if record is not None:
            row.update(title=record.get("title", ""), declared_title=record.get("title", ""),
                       declared_status=record.get("status", ""))
            depends_on = record.get("depends_on", [])
            if not isinstance(depends_on, list) or any(
                not isinstance(dep, str) or not TASK_NUMBER_RE.fullmatch(dep)
                for dep in depends_on
            ):
                row["dependency_error"] = "depends_on must contain four-digit subtask ids"
                blockers.append(f"Declared subtask {sub_id}: {row['dependency_error']}")
            else:
                row["depends_on"] = list(dict.fromkeys(depends_on))
        if folder is None:
            row["error"] = "directory missing on disk"
            blockers.append(f"Declared subtask {sub_id}: {row['error']}")
        else:
            try:
                data = json.loads((folder / "task.json").read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("task.json must be a JSON object")
            except FileNotFoundError:
                row["error"] = "task.json missing"
            except (ValueError, OSError) as exc:
                row.update(phase="invalid", error=f"cannot read task.json: {exc}")
            else:
                phase = data.get("phase", "unset")
                row.update(id=data.get("task_key", sub_id), task_key=data.get("task_key", sub_id),
                           title=data.get("title", row["title"]), phase=phase,
                           task_type=data.get("task_type", "unset"),
                           flow=data.get("flow", "unset"))
                if phase != "completed":
                    blockers.append(f"Subtask {sub_id}: phase is {phase!r}, not completed")
                elif project_root is not None and "acceptance_policy" in data:
                    if data["acceptance_policy"] != CASE_COVERAGE:
                        blockers.append(f"Subtask {sub_id}: unsupported acceptance_policy")
                    else:
                        _, evidence_problems = acceptance_state(
                            project_root, folder, data, current_stage(list_stages(folder))
                        )
                        blockers.extend(f"Subtask {sub_id}: {problem}" for problem in evidence_problems)
            if "error" in row:
                blockers.append(f"Subtask {sub_id}: {row['error']}")
        rows.append(row)
        by_id[sub_id] = row

    for sub_id, row in by_id.items():
        for dep in row.get("depends_on", []):
            if dep not in by_id:
                row["dependency_error"] = f"depends on unknown subtask {dep}"
                blockers.append(f"Subtask {sub_id}: {row['dependency_error']}")
            elif dep == sub_id:
                row["dependency_error"] = f"depends on itself ({dep})"
                blockers.append(f"Subtask dependency cycle: {sub_id} -> {sub_id}")

    visiting: list[str] = []
    visited: set[str] = set()
    reported: set[tuple[str, ...]] = set()

    def visit(node: str) -> None:
        if node in visited:
            return
        if node in visiting:
            cycle = tuple(visiting[visiting.index(node):] + [node])
            if cycle not in reported:
                reported.add(cycle)
                blockers.append(f"Subtask dependency cycle: {' -> '.join(cycle)}")
                for member in cycle[:-1]:
                    by_id[member]["dependency_error"] = "dependency cycle"
                    by_id[member]["readiness"] = "blocked"
            return
        visiting.append(node)
        for dep in by_id[node].get("depends_on", []):
            if dep in by_id and dep != node:
                visit(dep)
        visiting.pop()
        visited.add(node)

    for sub_id in by_id:
        visit(sub_id)

    for sub_id, row in by_id.items():
        if row["phase"] == "completed":
            row["ready"] = True
            row["readiness"] = "completed"
            continue
        if row.get("error") or row.get("dependency_error") or row["phase"] == "invalid":
            row["ready"] = False
            row["readiness"] = "blocked"
            continue
        pending = [
            dep for dep in row.get("depends_on", [])
            if by_id.get(dep, {}).get("phase") != "completed"
        ]
        if pending:
            row["ready"] = False
            row["readiness"] = "blocked"
            row["blocked_by"] = pending
            blockers.append(f"Subtask {sub_id}: blocked by {', '.join(pending)}")
        else:
            row["ready"] = True
            row["readiness"] = "ready"
    return rows, blockers


def check_subtasks_closed(root: Path, task_key: str) -> tuple[bool, list[str]]:
    """Compatibility helper for callers that pass a root and task key."""
    from .identity import task_dir

    tdir = task_dir(Path(root), task_key)
    try:
        data = json.loads((tdir / "task.json").read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("task.json must be a JSON object")
    except (ValueError, OSError) as exc:
        return False, [f"Task {task_key}: cannot read task.json: {exc}"]
    _, blockers = inspect_subtasks(tdir, data)
    return not blockers, blockers


# ---------------------------------------------------------------------------
# Path validation (doc/config/paths.yaml enforcement)
# ---------------------------------------------------------------------------


def load_paths_config(project_config: ProjectConfigOrPath) -> tuple[dict[str, Any] | None, list[str]]:
    """Return the parsed YAML for existing programmatic callers."""
    if isinstance(project_config, ProjectConfig):
        return project_config.raw_config, []
    config, errors = load_project_config(project_config)
    return (config.raw_config if config else None), errors


def validate_paths(project_config: ProjectConfig) -> list[str]:
    """Validate doc/ against declared paths in paths.yaml.

    Returns list of human-readable error messages (empty when valid).
    Checks:
      - every file under doc/ matches at least one allowed path pattern;
      - every declared path pattern has at least one matching file (unless template-only);
      - .md files under doc/architecture/ have valid frontmatter with required fields.
    """
    errors: list[str] = []

    root = project_config.root
    allowed_paths = project_config.get_allowed_paths()
    structure_rules = project_config.get_structure_rules()
    only_declared = structure_rules.get(ONLY_DECLARED_PATHS_KEY, True)
    frontmatter_required = structure_rules.get(FRONTMATTER_REQUIRED_FOR_KEY, [])
    config_name = project_config.config_path

    candidates = {project_config.doc_root, project_config.architecture_root,
                  project_config.tasks_root, project_config.schemas_root,
                  project_config.skills_root, project_config.task_conf_root, project_config.config_root}
    scan_roots = []
    for directory in sorted(candidates, key=lambda path: len(path.parts)):
        if directory.is_dir() and not any(directory.is_relative_to(parent) for parent in scan_roots):
            scan_roots.append(directory)

    actual_files: list[str] = []
    for directory in scan_roots:
        for path in directory.rglob("*"):
            rel = path.relative_to(root)
            if {"__pycache__", ".pytest_cache", ".git"}.intersection(rel.parts):
                continue
            if path.is_symlink() and not path.resolve().is_relative_to(root):
                errors.append(f"Path escapes project root: {rel}")
                continue
            if path.is_file():
                actual_files.append(rel.as_posix())

    if only_declared:
        for rel in sorted(actual_files):
            if not path_is_allowed(rel, allowed_paths):
                errors.append(f"Undeclared path in doc/: {rel} — not listed in {config_name} allowed_paths")

    for pattern in allowed_paths:
        if "{" not in pattern and "*" not in pattern and not (root / pattern).exists():
            errors.append(f"Declared path missing on disk: {pattern} — expected by {config_name}")

    # 3. Frontmatter required for architecture .md files
    import fnmatch

    # Use the resolved architecture root pattern for matching
    arch_root_rel = project_config.architecture_root.relative_to(project_config.root).as_posix()
    arch_md_files = [
        rel for rel in actual_files
        if rel.startswith(f"{arch_root_rel}/") and rel.endswith(".md")
    ]
    for rel in sorted(arch_md_files):
        if not any(fnmatch.fnmatch(rel, pat) for pat in frontmatter_required):
            continue
        full = project_config.root / rel
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
        project = project_config.get_project_section()
        doc_types = project.get(PROJECT_DOCUMENT_TYPES_KEY, [])
        if ftype and doc_types and ftype not in doc_types:
            errors.append(f"Unknown document type {ftype!r}: {rel}")
        fstatus = front.get("status")
        doc_statuses = project.get(PROJECT_DOCUMENT_STATUSES_KEY, [])
        if fstatus and doc_statuses and fstatus not in doc_statuses:
            errors.append(f"Unknown document status {fstatus!r}: {rel}")

    return errors
