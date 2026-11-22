"""Architecture store: documents, index, links and related-refs validation."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator, FormatChecker

from .body_validation import validate_document_body
from .project_config import ProjectConfig, UniqueKeyLoader


@dataclass
class Document:
    path: Path
    relative_path: str
    metadata: dict[str, Any]
    body: str


class ArchitectureStore:
    def __init__(self, project_config: ProjectConfig):
        self.project_config = project_config
        self.root = project_config.root
        self.docs = project_config.architecture_root
        self.document_schema_path = project_config.schemas_root / "document.schema.json"
        self.index_schema_path = project_config.schemas_root / "index.schema.json"
        self.index_path = project_config.index_path

    def _load_schema(self, path: Path) -> dict[str, Any]:
        try:
            schema = json.loads(path.read_text(encoding="utf-8"))
            Draft202012Validator.check_schema(schema)
            return schema
        except FileNotFoundError:
            raise ValueError(f"schema not found: {path.relative_to(self.root)}")
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON schema {path}: {exc}") from exc

    def _validate_instance(self, instance: Any, schema: dict[str, Any], label: str) -> list[str]:
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        errors = sorted(
            validator.iter_errors(instance),
            key=lambda e: list(map(str, e.absolute_path)),
        )
        result = []
        for err in errors:
            pointer = (
                "/" + "/".join(str(part) for part in err.absolute_path)
                if err.absolute_path
                else "/"
            )
            result.append(f"{label}{pointer}: {err.message}")
        return result

    @staticmethod
    def _parse_frontmatter(path: Path) -> tuple[dict[str, Any], str]:
        text = path.read_text(encoding="utf-8")
        import re

        FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
        match = FRONTMATTER.match(text)
        if not match:
            raise ValueError("missing YAML frontmatter delimited by ---")
        raw = match.group(1)
        try:
            metadata = yaml.load(raw, Loader=UniqueKeyLoader)
        except yaml.YAMLError as exc:
            raise ValueError(f"invalid/unsafe YAML frontmatter: {exc}") from exc
        if not isinstance(metadata, dict):
            raise ValueError("frontmatter must be a YAML mapping")
        return metadata, text[match.end():]

    def load_documents(self) -> tuple[list[Document], list[str]]:
        errors: list[str] = []
        docs: list[Document] = []
        if not self.docs.is_dir():
            return [], [f"architecture root not found: {self.docs}"]
        schema = self._load_schema(self.document_schema_path)
        seen: dict[str, str] = {}
        for path in sorted(self.docs.rglob("*.md")):
            # The top-level README is a human-authored navigation page, not an indexed record.
            if path == self.docs / "README.md":
                continue
            try:
                metadata, body = self._parse_frontmatter(path)
            except (OSError, ValueError) as exc:
                errors.append(f"{path.relative_to(self.root)}: {exc}")
                continue
            rel = path.relative_to(self.docs).as_posix()
            errors.extend(self._validate_instance(metadata, schema, f"{rel}:"))
            doc_id = metadata.get("id")
            if isinstance(doc_id, str):
                if doc_id in seen:
                    errors.append(f"{rel}: duplicate id {doc_id!r}; first seen in {seen[doc_id]}")
                else:
                    seen[doc_id] = rel
            docs.append(Document(path, rel, metadata, body))
        return docs, errors

    @staticmethod
    def _body_without_fences(body: str) -> str:
        import re

        FENCE = re.compile(r"^\s*(```+|~~~+)")
        output: list[str] = []
        fence_char: str | None = None
        fence_len = 0
        for line in body.splitlines():
            marker = FENCE.match(line)
            if marker:
                token = marker.group(1)
                char = token[0]
                if fence_char is None:
                    fence_char, fence_len = char, len(token)
                elif char == fence_char and len(token) >= fence_len:
                    fence_char, fence_len = None, 0
                continue
            if fence_char is None:
                output.append(line)
        return "\n".join(output)

    def validate_links(self, docs: list[Document]) -> list[str]:
        errors: list[str] = []
        project_root = self.root.resolve()
        import re
        from urllib.parse import unquote, urlparse

        LINK = re.compile(
            r"\[[^\]]*\]\((<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)"
        )
        for doc in docs:
            body = self._body_without_fences(doc.body)
            for match in LINK.finditer(body):
                target_text = match.group(1)
                if target_text.startswith("<") and target_text.endswith(">"):
                    target_text = target_text[1:-1]
                target_text = unquote(target_text)
                parsed = urlparse(target_text)
                if (
                    parsed.scheme in {"http", "https", "mailto", "tel"}
                    or target_text.startswith("#")
                ):
                    continue
                target_path = target_text.split("#", 1)[0].split("?", 1)[0]
                if not target_path:
                    continue
                candidate = (doc.path.parent / target_path).resolve()
                try:
                    candidate.relative_to(project_root)
                except ValueError:
                    errors.append(
                        f"{doc.relative_path}: local link escapes project root: {target_text}"
                    )
                    continue
                if not candidate.exists():
                    errors.append(
                        f"{doc.relative_path}: broken local link: {target_text}"
                    )
        return errors

    def validate_related(self, docs: list[Document]) -> list[str]:
        ids = {d.metadata.get("id") for d in docs if isinstance(d.metadata.get("id"), str)}
        errors: list[str] = []
        for doc in docs:
            related = doc.metadata.get("related", [])
            if isinstance(related, list):
                for ref in related:
                    if isinstance(ref, str) and ref not in ids:
                        errors.append(f"{doc.relative_path}: unresolved related id {ref!r}")
        return errors

    @staticmethod
    def make_index(docs: list[Document]) -> dict[str, Any]:
        records = []
        for doc in docs:
            md = doc.metadata
            record = {
                "id": md["id"],
                "type": md["type"],
                "title": md["title"],
                "summary": md["summary"],
                "status": md["status"],
                "path": doc.relative_path,
            }
            for key in ("domain", "related", "source_refs", "applies_to"):
                if key in md:
                    record[key] = md[key]
            # Every indexed document carries an explicit implementation flag.
            record["implemented"] = md.get("implemented", False)
            records.append(record)
        records.sort(key=lambda x: x["id"])
        return {"index_schema_version": 1, "documents": records}

    def build_index(self) -> tuple[dict[str, Any] | None, list[str]]:
        docs, errors = self.load_documents()
        errors.extend(self.validate_links(docs))
        errors.extend(self.validate_related(docs))
        if errors:
            return None, errors
        index = self.make_index(docs)
        index_schema = self._load_schema(self.index_schema_path)
        errors.extend(self._validate_instance(index, index_schema, "index.json:"))
        return (None if errors else index), errors

    def validate(self, check_index: bool = True) -> list[str]:
        docs, errors = self.load_documents()
        errors.extend(self.validate_links(docs))
        errors.extend(self.validate_related(docs))
        # Validate document bodies by type schema
        schemas_dir = self.project_config.schemas_root
        for doc in docs:
            doc_type = doc.metadata.get("type")
            if doc_type:
                body_errors = validate_document_body(doc.body, doc_type, schemas_dir)
                for be in body_errors:
                    errors.append(f"{doc.relative_path}: {be}")
        if check_index:
            expected = self.make_index(docs) if not errors else None
            if expected is not None:
                index_schema = self._load_schema(self.index_schema_path)
                errors.extend(self._validate_instance(expected, index_schema, "index.json:"))
                try:
                    actual = json.loads(self.index_path.read_text(encoding="utf-8"))
                except FileNotFoundError:
                    errors.append(
                        f"{self.index_path.relative_to(self.root)}: missing; run `python3 doc/tools/arch/__main__.py index build`"
                    )
                except json.JSONDecodeError as exc:
                    errors.append(f"{self.index_path.relative_to(self.root)}: invalid JSON: {exc}")
                else:
                    errors.extend(self._validate_instance(actual, index_schema, "index.json:"))
                    if actual != expected:
                        errors.append(f"{self.index_path.relative_to(self.root)}: stale; run `python3 doc/tools/arch/__main__.py index build`")
        return errors

    def write_index(self, index: dict[str, Any]) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(index, ensure_ascii=False, indent=2) + "\n"
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.index_path.parent, delete=False
        ) as tmp:
            tmp.write(payload)
            temp_path = Path(tmp.name)
        temp_path.replace(self.index_path)