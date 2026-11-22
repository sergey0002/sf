"""Project configuration loader for arch CLI.

Loads and resolves the project YAML configuration (paths.yaml) with support
for explicit --config override and path resolution relative to project root.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .constants import (
    PATHS_CONFIG_RELATIVE,
    ROOTS_KEY,
    ROOT_ARCHITECTURE_KEY,
    ROOT_TASKS_KEY,
    ROOT_SCHEMAS_KEY,
    ROOT_TASK_CONF_KEY,
    ROOT_SKILLS_KEY,
    ROOT_REFERENCE_KEY,
    ROOT_INDEX_KEY,
    ROOT_CONFIG_KEY,
)


class UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict:
    loader.flatten_mapping(node)
    result: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in result
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                "found an unhashable key", key_node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping", node.start_mark,
                f"found duplicate key {key!r}", key_node.start_mark,
            )
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping
)


DEFAULT_ROOT_SUFFIXES = {
    ROOT_ARCHITECTURE_KEY: "architecture",
    ROOT_TASKS_KEY: "tasks",
    ROOT_SCHEMAS_KEY: "architecture/schemas",
    ROOT_TASK_CONF_KEY: "config/task-conf",
    ROOT_SKILLS_KEY: "skills",
    ROOT_CONFIG_KEY: "config",
}
DEFAULT_ROOTS = {
    key: f"doc/{suffix}" for key, suffix in DEFAULT_ROOT_SUFFIXES.items()
}
DEFAULT_ROOTS[ROOT_REFERENCE_KEY] = "data"
DEFAULT_ROOTS[ROOT_INDEX_KEY] = "index.json"


class ProjectConfig:
    """Resolved project configuration with all paths relative to project root."""

    def __init__(
        self,
        root: Path,
        config_path: Path,
        raw_config: dict[str, Any],
        roots: dict[str, Path],
    ):
        self.root = root.resolve()
        self.config_path = config_path
        self.raw_config = raw_config
        self.roots = roots  # Already resolved to absolute paths

    @property
    def architecture_root(self) -> Path:
        return self.roots[ROOT_ARCHITECTURE_KEY]

    @property
    def tasks_root(self) -> Path:
        return self.roots[ROOT_TASKS_KEY]

    @property
    def schemas_root(self) -> Path:
        return self.roots[ROOT_SCHEMAS_KEY]

    @property
    def task_conf_root(self) -> Path:
        return self.roots[ROOT_TASK_CONF_KEY]

    @property
    def skills_root(self) -> Path:
        return self.roots[ROOT_SKILLS_KEY]

    @property
    def reference_root(self) -> Path:
        return self.roots[ROOT_REFERENCE_KEY]

    @property
    def index_path(self) -> Path:
        return self.roots[ROOT_INDEX_KEY]

    @property
    def config_root(self) -> Path:
        return self.roots[ROOT_CONFIG_KEY]

    @property
    def doc_root(self) -> Path:
        return (self.root / self.raw_config.get("doc_root", "doc")).resolve()

    def expand_pattern(self, pattern: str) -> str:
        """Expand configured roots, leaving record-level placeholders intact."""
        pattern = pattern.replace("{doc_root}", self.doc_root.relative_to(self.root).as_posix())
        pattern = pattern.replace("{architecture}/{index}", "{index}")
        for key, path in self.roots.items():
            placeholder = "{" + key + "}"
            if placeholder in pattern:
                pattern = pattern.replace(placeholder, path.relative_to(self.root).as_posix())
        return pattern

    def get_allowed_paths(self) -> list[str]:
        return [self.expand_pattern(pattern) for pattern in self.raw_config.get("allowed_paths", [])]

    def get_structure_rules(self) -> dict[str, Any]:
        rules = dict(self.raw_config.get("structure_rules", {}))
        for key in ("frontmatter_required_for", "generated_files"):
            if key in rules:
                rules[key] = [self.expand_pattern(pattern) for pattern in rules[key]]
        return rules

    def get_project_section(self) -> dict[str, Any]:
        """Get the project section from config."""
        return self.raw_config.get("project", {}) or {}

    def resolve_path(self, relative_path: str) -> Path:
        """Resolve a path relative to project root."""
        return (self.root / relative_path).resolve()

    def is_path_allowed(self, relative_path: str) -> bool:
        """Check if a path is allowed by the configuration."""
        from .constants import path_is_allowed
        allowed = self.get_allowed_paths()
        return path_is_allowed(relative_path, allowed)


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{field} must be a list of non-empty strings")
    return value


def _resolve_location(base: Path, value: Any, field: str, *, contained: bool = True) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty path string")
    path = (base / value).resolve()
    if contained and not path.is_relative_to(base):
        raise ValueError(f"{field} ({value}) escapes {base}")
    return path


def _validate_sections(config: ProjectConfig) -> None:
    raw = config.raw_config
    project = raw.get("project", {})
    if not isinstance(project, dict):
        raise ValueError("project must be a mapping")
    for key in ("document_types", "document_statuses", "task_types", "phases", "risk_levels",
                "source_types", "task_schema_required_fields", "task_statuses"):
        if key in project:
            _string_list(project[key], f"project.{key}")

    rules = raw.get("structure_rules", {})
    if not isinstance(rules, dict):
        raise ValueError("structure_rules must be a mapping")
    if "only_declared_paths" in rules and not isinstance(rules["only_declared_paths"], bool):
        raise ValueError("structure_rules.only_declared_paths must be a boolean")
    _string_list(rules.get("architecture_doc_extensions", []), "structure_rules.architecture_doc_extensions")
    for field, patterns in (
        ("allowed_paths", raw.get("allowed_paths", [])),
        ("structure_rules.frontmatter_required_for", rules.get("frontmatter_required_for", [])),
        ("structure_rules.generated_files", rules.get("generated_files", [])),
    ):
        for pattern in _string_list(patterns, field):
            try:
                path = Path(config.expand_pattern(pattern))
            except ValueError as exc:
                raise ValueError(f"{field}: {pattern!r} refers to a root outside the project") from exc
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"{field}: {pattern!r} must stay inside the project")


def load_project_config(
    project_root: Path,
    config_override: Path | None = None,
) -> tuple[ProjectConfig | None, list[str]]:
    """Read the chosen YAML and resolve its paths before dispatching a command."""
    root = project_root.resolve()
    config_path = root / (config_override if config_override is not None else PATHS_CONFIG_RELATIVE)
    try:
        config_path = config_path.resolve()
        raw = yaml.load(config_path.read_text(encoding="utf-8"), Loader=UniqueKeyLoader)
        if not isinstance(raw, dict):
            raise ValueError("config must be a YAML mapping")
        raw_roots = raw.get(ROOTS_KEY, {})
        if not isinstance(raw_roots, dict):
            raise ValueError("roots must be a mapping")
        for key in raw_roots:
            if key not in DEFAULT_ROOTS:
                raise ValueError(f"unknown roots key: {key!r}")

        doc_root_value = raw.get("doc_root", "doc")
        doc_root = _resolve_location(root, doc_root_value, "doc_root")
        doc_prefix = Path(doc_root_value).as_posix().strip("/")
        roots = {}
        for key, default in DEFAULT_ROOTS.items():
            if key == ROOT_INDEX_KEY:
                continue
            if key in DEFAULT_ROOT_SUFFIXES:
                default = f"{doc_prefix}/{DEFAULT_ROOT_SUFFIXES[key]}"
            path = _resolve_location(root, raw_roots.get(key, default), f"roots.{key}",
                                     contained=key != ROOT_REFERENCE_KEY)
            if key != ROOT_REFERENCE_KEY and not path.is_dir():
                raise ValueError(f"roots.{key} directory not found: {path}")
            roots[key] = path

        index = raw_roots.get(ROOT_INDEX_KEY, DEFAULT_ROOTS[ROOT_INDEX_KEY])
        if not isinstance(index, str) or not index.strip() or Path(index).is_absolute():
            raise ValueError("roots.index must be a relative path inside roots.architecture")
        index_path = _resolve_location(roots[ROOT_ARCHITECTURE_KEY], index, "roots.index")
        if index_path == roots[ROOT_ARCHITECTURE_KEY] or (index_path.exists() and not index_path.is_file()):
            raise ValueError(f"roots.index must name a file: {index_path}")
        roots[ROOT_INDEX_KEY] = index_path

        config = ProjectConfig(root, config_path, raw, roots)
        _validate_sections(config)
    except yaml.YAMLError as exc:
        return None, [f"{config_path} (project root {root}): Invalid YAML: {exc}"]
    except (ValueError, OSError, RuntimeError) as exc:
        return None, [f"{config_path} (project root {root}): {exc}"]
    return config, []
