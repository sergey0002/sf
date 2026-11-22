"""Document operations: addressable sections, search, context and impact.

The CLI exposes deterministic mechanics. Relevance, authority and acceptance
remain the agent's judgement; these helpers only report declared links, hashes
and observable state.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import yaml

from .project_config import ProjectConfig, UniqueKeyLoader
from .sections import (
    anchor_exists,
    find_section,
    parse_sections,
    section_map,
    sha256_file,
    sha256_text,
    split_frontmatter,
    slugify,
)
from .store import ArchitectureStore, Document
from .subtask import current_stage, list_stages
from .task_ops import task_or_subtask_paths

DEFAULT_READ_BYTES = 32768
DEFAULT_CONTEXT_BYTES = 8192
ARCHIVED_STATUSES = {"superseded", "deprecated", "rejected"}
CONTRACT_TYPES = {
    "system", "system-overview", "architecture-view", "domain", "capability",
    "capability-spec", "glossary", "entity", "data-view", "flow", "rule-set",
    "integration", "cross-cutting-concept", "quality-view", "security-view",
    "deployment-operations-view", "constraints-risks", "verification-map",
    "component-view", "system-context", "quality-attributes", "implementation-spec",
    "testing-spec", "runbook",
}
LINK_RE = re.compile(r"\[[^\]]*\]\((<[^>]+>|[^\s)]+)(?:\s+[^)]*)?\)")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
DOC_REF_RE = re.compile(r"^(?P<id>[A-Z][A-Za-z0-9_-]*)(?:#(?P<anchor>.+))?$")


class DocOpsError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        field: str | None = None,
        suggestion: str | None = None,
        exit_code: int = 1,
        data: Any = None,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field
        self.suggestion = suggestion
        self.exit_code = exit_code
        self.data = data


def _relative(path: Path, config: ProjectConfig) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(config.root).as_posix()
    except ValueError:
        return resolved.as_posix()


def _load_documents(store: ArchitectureStore) -> list[Document]:
    docs, errors = store.load_documents()
    if errors:
        raise DocOpsError(
            "DOC-LOAD",
            "; ".join(errors),
            suggestion="fix the reported architecture documents, then rerun",
        )
    return docs


def _load_documents_tolerant(store: ArchitectureStore) -> tuple[list[Document], list[str]]:
    return store.load_documents()


def _split_ref(ref: str) -> tuple[str, str | None]:
    doc_id, sep, anchor = ref.partition("#")
    doc_id = doc_id.strip()
    anchor = anchor.strip() if sep else None
    if not doc_id:
        raise DocOpsError(
            "ARGS", f"invalid document reference {ref!r}",
            field="ref", suggestion="use DOC-ID or DOC-ID#section-id",
            exit_code=2,
        )
    return doc_id, anchor or None


def _doc_by_id(docs: list[Document], doc_id: str) -> Document:
    matches = [doc for doc in docs if doc.metadata.get("id") == doc_id]
    if not matches:
        raise DocOpsError(
            "DOC-NOT-FOUND", f"document id {doc_id!r} not found",
            field="id", suggestion="use `arch docs tree` or `arch list` to find the ID",
            exit_code=1,
        )
    if len(matches) > 1:
        raise DocOpsError(
            "DOC-AMBIGUOUS", f"document id {doc_id!r} resolves to {len(matches)} documents",
            field="id", suggestion="fix the duplicate ID before reading", exit_code=1,
        )
    return matches[0]


def _frontmatter_offset(path: Path, body: str) -> int:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return 0
    if not text.endswith(body):
        return 0
    return text[: len(text) - len(body)].count("\n")


def read_section(
    store: ArchitectureStore, ref: str, max_bytes: int = DEFAULT_READ_BYTES,
) -> dict[str, Any]:
    if max_bytes <= 0:
        raise DocOpsError("ARGS", "--max-bytes must be positive", field="max_bytes", exit_code=2)
    doc_id, anchor = _split_ref(ref)
    if anchor is None:
        raise DocOpsError(
            "ARGS", "read requires a section anchor: DOC-ID#section-id",
            field="ref", suggestion="use `arch show <id>` for the whole document",
            exit_code=2,
        )
    docs = _load_documents(store)
    doc = _doc_by_id(docs, doc_id)
    sections = parse_sections(doc.body)
    section, problem = find_section(sections, anchor)
    if section is None:
        raise DocOpsError(
            "SECTION-AMBIGUOUS" if problem == "ambiguous" else "SECTION-NOT-FOUND",
            f"{doc_id}#{anchor}: section is {problem}",
            field="ref",
            suggestion=f"run `arch docs toc {doc_id}` or use an explicit {{#anchor}}",
            exit_code=1,
        )
    payload = section.text.encode("utf-8")
    if len(payload) > max_bytes:
        raise DocOpsError(
            "SECTION-TOO-LARGE",
            f"{doc_id}#{anchor}: {len(payload)} bytes exceeds --max-bytes {max_bytes}",
            field="max_bytes",
            suggestion=(
                f"raise --max-bytes to at least {len(payload)} or read a subsection; "
                "partial text is never returned as the full section"
            ),
            exit_code=1,
            data={"section_bytes": len(payload), "max_bytes": max_bytes},
        )
    offset = _frontmatter_offset(doc.path, doc.body)
    return {
        "doc_id": doc_id,
        "path": _relative(doc.path, store.project_config),
        "anchor": section.anchor,
        "anchor_kind": section.anchor_kind,
        "stable": section.stable,
        "title": section.title,
        "heading_path": list(section.heading_path),
        "line_start": offset + section.line_start,
        "line_end": offset + section.line_end,
        "bytes": len(payload),
        "sha256": sha256_file(doc.path),
        "doc_status": doc.metadata.get("status"),
        "content": section.text,
    }


def table_of_contents(store: ArchitectureStore, doc_id: str) -> dict[str, Any]:
    docs = _load_documents(store)
    doc = _doc_by_id(docs, doc_id)
    offset = _frontmatter_offset(doc.path, doc.body)
    return {
        "doc_id": doc_id,
        "path": _relative(doc.path, store.project_config),
        "status": doc.metadata.get("status"),
        "sections": [
            {
                "anchor": item.anchor,
                "anchor_kind": item.anchor_kind,
                "stable": item.stable,
                "level": item.level,
                "title": item.title,
                "heading_path": list(item.heading_path),
                "line_start": offset + item.line_start,
                "line_end": offset + item.line_end,
            }
            for item in parse_sections(doc.body)
        ],
    }


def _tokens(query: str) -> list[str]:
    return [token for token in query.casefold().split() if token]


def _has_all(text: str, tokens: list[str]) -> bool:
    folded = text.casefold()
    return all(token in folded for token in tokens)


def _count(text: str, tokens: list[str]) -> int:
    folded = text.casefold()
    return sum(folded.count(token) for token in tokens)


def _snippet(text: str, tokens: list[str], limit: int = 240) -> str:
    collapsed = re.sub(r"\s+", " ", text).strip()
    folded = collapsed.casefold()
    positions = [folded.find(token) for token in tokens if folded.find(token) >= 0]
    start = min(positions) if positions else 0
    start = max(0, start - limit // 3)
    fragment = collapsed[start:start + limit].strip()
    if start > 0:
        fragment = "…" + fragment
    if start + limit < len(collapsed):
        fragment = fragment + "…"
    return fragment


def _aliases(metadata: dict[str, Any]) -> list[str]:
    value = metadata.get("aliases")
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str)]
    return []


def _first_heading(body: str) -> str | None:
    for section in parse_sections(body):
        return section.title
    return None


def _reference_documents(reference_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not reference_root.is_dir():
        return records
    for path in sorted(reference_root.rglob("*.md")):
        try:
            if path.stat().st_size > 2_000_000:
                continue
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        frontmatter, body, _ = split_frontmatter(text)
        metadata: dict[str, Any] = {}
        if frontmatter:
            try:
                loaded = yaml.load(frontmatter, Loader=UniqueKeyLoader)
                if isinstance(loaded, dict):
                    metadata = loaded
            except yaml.YAMLError:
                metadata = {}
        doc_id = metadata.get("id")
        if not isinstance(doc_id, str) or not doc_id:
            doc_id = path.relative_to(reference_root).with_suffix("").as_posix()
        records.append({
            "id": doc_id,
            "type": metadata.get("type") or "reference",
            "title": metadata.get("title") or _first_heading(body) or path.stem,
            "summary": metadata.get("summary") or "",
            "status": metadata.get("status") or "reference",
            "path": path,
            "body": body,
            "metadata": metadata,
        })
    return records


def _hit(
    *, doc_id: str, source: str, doc_type: Any, title: str, status: Any,
    path: Path, config: ProjectConfig, anchor: str | None, anchor_kind: str | None,
    line: int | None, match: str, score: int, snippet: str,
) -> dict[str, Any]:
    return {
        "id": doc_id,
        "source": source,
        "type": doc_type,
        "title": title,
        "status": status,
        "path": _relative(path, config),
        "anchor": anchor,
        "anchor_kind": anchor_kind,
        "line": line,
        "match": match,
        "score": score,
        "snippet": snippet,
    }


def _rank_product(
    doc: Document, tokens: list[str], query: str, config: ProjectConfig,
) -> dict[str, Any] | None:
    metadata = doc.metadata
    doc_id = str(metadata["id"])
    aliases = _aliases(metadata)
    title = str(metadata.get("title") or "")
    summary = str(metadata.get("summary") or "")
    body = doc.body
    folded_query = query.casefold()
    all_text = "\n".join([doc_id, *aliases, title, summary, body])

    if not _has_all(all_text, tokens):
        return None

    if folded_query in {doc_id.casefold(), *(alias.casefold() for alias in aliases)}:
        return _hit(
            doc_id=doc_id, source="product", doc_type=metadata.get("type"),
            title=title, status=metadata.get("status"), path=doc.path, config=config,
            anchor=None, anchor_kind=None, line=None, match="id",
            score=1000, snippet=_snippet(title or doc_id, tokens),
        )

    occurrences = _count(all_text, tokens)
    bonus = min(50, occurrences * 5)
    if _has_all(doc_id, tokens):
        return _hit(
            doc_id=doc_id, source="product", doc_type=metadata.get("type"),
            title=title, status=metadata.get("status"), path=doc.path, config=config,
            anchor=None, anchor_kind=None, line=None, match="id",
            score=400 + bonus, snippet=_snippet(title or doc_id, tokens),
        )
    if _has_all(title, tokens):
        return _hit(
            doc_id=doc_id, source="product", doc_type=metadata.get("type"),
            title=title, status=metadata.get("status"), path=doc.path, config=config,
            anchor=None, anchor_kind=None, line=None, match="title",
            score=300 + bonus, snippet=_snippet(title, tokens),
        )
    if _has_all(summary, tokens):
        return _hit(
            doc_id=doc_id, source="product", doc_type=metadata.get("type"),
            title=title, status=metadata.get("status"), path=doc.path, config=config,
            anchor=None, anchor_kind=None, line=None, match="summary",
            score=200 + bonus, snippet=_snippet(summary, tokens),
        )

    sections = parse_sections(body)
    for section in sections:
        if _has_all(section.title, tokens):
            offset = _frontmatter_offset(doc.path, body)
            return _hit(
                doc_id=doc_id, source="product", doc_type=metadata.get("type"),
                title=title, status=metadata.get("status"), path=doc.path, config=config,
                anchor=section.anchor, anchor_kind=section.anchor_kind,
                line=offset + section.line_start, match="heading",
                score=150 + bonus, snippet=_snippet(section.text, tokens),
            )

    for index, line in enumerate(body.splitlines(), start=1):
        if _has_all(line, tokens):
            enclosing = [section for section in sections if section.line_start <= index]
            section = enclosing[-1] if enclosing else None
            offset = _frontmatter_offset(doc.path, body)
            return _hit(
                doc_id=doc_id, source="product", doc_type=metadata.get("type"),
                title=title, status=metadata.get("status"), path=doc.path, config=config,
                anchor=section.anchor if section else None,
                anchor_kind=section.anchor_kind if section else None,
                line=offset + index, match="body", score=100 + bonus,
                snippet=_snippet(line, tokens),
            )
    return None


def _rank_reference(
    record: dict[str, Any], tokens: list[str], query: str, config: ProjectConfig,
) -> dict[str, Any] | None:
    doc_id = record["id"]
    title = record["title"]
    summary = record["summary"]
    body = record["body"]
    folded_query = query.casefold()
    all_text = "\n".join([doc_id, title, summary, body])
    if not _has_all(all_text, tokens):
        return None
    if folded_query == doc_id.casefold():
        return _hit(
            doc_id=doc_id, source="reference", doc_type=record["type"], title=title,
            status=record["status"], path=record["path"], config=config, anchor=None,
            anchor_kind=None, line=None, match="id", score=1000,
            snippet=_snippet(title or doc_id, tokens),
        )
    occurrences = _count(all_text, tokens)
    bonus = min(50, occurrences * 5)
    if _has_all(doc_id, tokens):
        return _hit(
            doc_id=doc_id, source="reference", doc_type=record["type"], title=title,
            status=record["status"], path=record["path"], config=config, anchor=None,
            anchor_kind=None, line=None, match="id", score=400 + bonus,
            snippet=_snippet(title or doc_id, tokens),
        )
    if _has_all(title, tokens):
        return _hit(
            doc_id=doc_id, source="reference", doc_type=record["type"], title=title,
            status=record["status"], path=record["path"], config=config, anchor=None,
            anchor_kind=None, line=None, match="title", score=300 + bonus,
            snippet=_snippet(title, tokens),
        )
    if _has_all(summary, tokens):
        return _hit(
            doc_id=doc_id, source="reference", doc_type=record["type"], title=title,
            status=record["status"], path=record["path"], config=config, anchor=None,
            anchor_kind=None, line=None, match="summary", score=200 + bonus,
            snippet=_snippet(summary, tokens),
        )
    sections = parse_sections(body)
    for section in sections:
        if _has_all(section.title, tokens):
            return _hit(
                doc_id=doc_id, source="reference", doc_type=record["type"], title=title,
                status=record["status"], path=record["path"], config=config,
                anchor=section.anchor, anchor_kind=section.anchor_kind,
                line=section.line_start, match="heading", score=150 + bonus,
                snippet=_snippet(section.text, tokens),
            )
    for index, line in enumerate(body.splitlines(), start=1):
        if _has_all(line, tokens):
            return _hit(
                doc_id=doc_id, source="reference", doc_type=record["type"], title=title,
                status=record["status"], path=record["path"], config=config, anchor=None,
                anchor_kind=None, line=index, match="body", score=100 + bonus,
                snippet=_snippet(line, tokens),
            )
    return None


def search(
    store: ArchitectureStore,
    query: str,
    *,
    scope: str = "product",
    limit: int = 5,
    include_archived: bool = False,
) -> dict[str, Any]:
    tokens = _tokens(query)
    if not tokens:
        raise DocOpsError("ARGS", "search query is empty", field="query", exit_code=2)
    if limit < 1:
        raise DocOpsError("ARGS", "--limit must be positive", field="limit", exit_code=2)
    if scope not in {"product", "reference", "all"}:
        raise DocOpsError("ARGS", f"unknown scope {scope!r}", field="scope", exit_code=2)

    config = store.project_config
    hits: list[dict[str, Any]] = []
    notes: list[str] = []

    if scope in {"product", "all"}:
        docs = _load_documents(store)
        for doc in docs:
            status = doc.metadata.get("status")
            if not include_archived and status in ARCHIVED_STATUSES:
                continue
            hit = _rank_product(doc, tokens, query, config)
            if hit is not None:
                hits.append(hit)

    if scope in {"reference", "all"}:
        reference_root = config.reference_root
        records = _reference_documents(reference_root)
        if not reference_root.is_dir():
            notes.append("reference root not found; reference scope returned no documents")
        for record in records:
            hit = _rank_reference(record, tokens, query, config)
            if hit is not None:
                hits.append(hit)

    hits.sort(key=lambda item: (-item["score"], item["id"], item["path"], item["line"] or 0))
    total = len(hits)
    return {
        "query": query,
        "scope": scope,
        "limit": limit,
        "total_matched": total,
        "hits": hits[:limit],
        "notes": notes,
    }


def _scan_links(path: Path, body: str):
    fence_char: str | None = None
    fence_len = 0
    for index, line in enumerate(body.splitlines(), start=1):
        marker = FENCE_RE.match(line)
        if marker:
            token = marker.group(1)
            char = token[0]
            if fence_char is None:
                fence_char, fence_len = char, len(token)
            elif char == fence_char and len(token) >= fence_len:
                fence_char, fence_len = None, 0
            continue
        if fence_char is not None:
            continue
        for match in LINK_RE.finditer(line):
            target = match.group(1)
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            yield index, unquote(target)


def check_links(store: ArchitectureStore) -> dict[str, Any]:
    config = store.project_config
    docs, load_errors = _load_documents_tolerant(store)
    incidents: list[dict[str, Any]] = [
        {
            "code": "DOC-LOAD",
            "message": error,
            "source": None,
            "line": None,
            "target": None,
            "anchor": None,
        }
        for error in load_errors
    ]
    project_root = config.root.resolve()
    section_cache: dict[Path, list] = {}

    def sections_for(path: Path):
        resolved = path.resolve()
        if resolved not in section_cache:
            try:
                text = resolved.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                section_cache[resolved] = []
            else:
                _, body, _ = split_frontmatter(text)
                section_cache[resolved] = parse_sections(body)
        return section_cache[resolved]

    for doc in docs:
        offset = _frontmatter_offset(doc.path, doc.body)
        for line_no, target in _scan_links(doc.path, doc.body):
            parsed = urlparse(target)
            if parsed.scheme in {"http", "https", "mailto", "tel"}:
                continue
            if not target:
                continue
            path_part, _, anchor = target.partition("#")
            path_part = path_part.split("?", 1)[0]
            source = _relative(doc.path, config)
            line = offset + line_no
            if not path_part:
                if anchor and not anchor_exists(sections_for(doc.path), anchor):
                    incidents.append({
                        "code": "DOC-ANCHOR",
                        "message": f"{source}:{line}: missing anchor #{anchor} in the same document",
                        "source": source, "line": line, "target": target, "anchor": anchor,
                    })
                continue
            candidate = (doc.path.parent / path_part).resolve()
            try:
                candidate.relative_to(project_root)
            except ValueError:
                incidents.append({
                    "code": "DOC-LINK",
                    "message": f"{source}:{line}: local link escapes project root: {target}",
                    "source": source, "line": line, "target": target, "anchor": anchor or None,
                })
                continue
            if not candidate.exists():
                incidents.append({
                    "code": "DOC-LINK",
                    "message": f"{source}:{line}: broken local link: {target}",
                    "source": source, "line": line, "target": target, "anchor": anchor or None,
                })
                continue
            if anchor and candidate.suffix == ".md" and not anchor_exists(sections_for(candidate), anchor):
                incidents.append({
                    "code": "DOC-ANCHOR",
                    "message": f"{source}:{line}: missing anchor #{anchor} in {_relative(candidate, config)}",
                    "source": source, "line": line, "target": target, "anchor": anchor,
                })

    incidents.sort(key=lambda item: (item["source"] or "", item["line"] or 0, item["code"]))
    return {
        "scanned_documents": len(docs),
        "incident_count": len(incidents),
        "incidents": incidents,
    }


def _authority(doc_type: Any, source: str) -> str:
    if source == "reference":
        return "reference"
    if doc_type == "decision":
        return "adr"
    if doc_type in CONTRACT_TYPES:
        return "contract"
    return "document"


def _doc_item(
    doc: Document, ref: str, declared_by: list[str], config: ProjectConfig,
    anchor: str | None = None,
) -> dict[str, Any]:
    status = doc.metadata.get("status")
    state = "superseded" if status in {"superseded", "deprecated"} else "ok"
    item: dict[str, Any] = {
        "kind": "document",
        "ref": ref,
        "doc_id": doc.metadata.get("id"),
        "authority": _authority(doc.metadata.get("type"), "product"),
        "type": doc.metadata.get("type"),
        "title": doc.metadata.get("title"),
        "status": status,
        "path": _relative(doc.path, config),
        "sha256": sha256_file(doc.path),
        "declared_by": sorted(set(declared_by)),
        "reason": f"declared in {', '.join(sorted(set(declared_by)))}",
        "state": state,
    }
    if status == "draft":
        item["state"] = "draft"
    if anchor:
        sections = parse_sections(doc.body)
        section, problem = find_section(sections, anchor)
        item["anchor"] = anchor
        if section is None:
            item["state"] = "missing_anchor"
            item["anchor_problem"] = problem
        else:
            item["anchor_kind"] = section.anchor_kind
            item["stable"] = section.stable
            item["line_start"] = section.line_start
            item["line_end"] = section.line_end
            item["section_title"] = section.title
    summary = doc.metadata.get("summary")
    if isinstance(summary, str):
        item["summary"] = summary
    return item


def _path_item(
    config: ProjectConfig, ref: str, declared_by: list[str], docs_by_id: dict[str, Document],
) -> dict[str, Any]:
    path_part, _, anchor = ref.partition("#")
    path_part = path_part.strip()
    anchor = anchor.strip() or None
    if DOC_REF_RE.fullmatch(ref) and path_part in docs_by_id:
        return _doc_item(docs_by_id[path_part], ref, declared_by, config, anchor)
    if DOC_REF_RE.fullmatch(path_part) and path_part in docs_by_id and anchor is None:
        return _doc_item(docs_by_id[path_part], ref, declared_by, config)

    candidate = (config.root / path_part).resolve()
    item: dict[str, Any] = {
        "kind": "file",
        "ref": ref,
        "path": path_part,
        "declared_by": sorted(set(declared_by)),
        "reason": f"declared in {', '.join(sorted(set(declared_by)))}",
    }
    try:
        candidate.relative_to(config.root.resolve())
    except ValueError:
        item.update(state="missing", problem="path escapes the project root")
        return item
    if not candidate.is_file():
        item.update(state="missing", problem="file not found")
        return item
    item["sha256"] = sha256_file(candidate)
    item["bytes"] = candidate.stat().st_size
    if candidate.is_relative_to(config.architecture_root):
        try:
            text = candidate.read_text(encoding="utf-8")
            frontmatter, body, _ = split_frontmatter(text)
            metadata = yaml.load(frontmatter, Loader=UniqueKeyLoader) if frontmatter else {}
            if not isinstance(metadata, dict):
                metadata = {}
        except (OSError, UnicodeDecodeError, yaml.YAMLError):
            metadata, body = {}, ""
        doc_id = metadata.get("id")
        if isinstance(doc_id, str) and doc_id:
            item["doc_id"] = doc_id
            item["authority"] = _authority(metadata.get("type"), "product")
            item["title"] = metadata.get("title")
            item["status"] = metadata.get("status")
            item["type"] = metadata.get("type")
            if isinstance(metadata.get("summary"), str):
                item["summary"] = metadata["summary"]
            if anchor:
                sections = parse_sections(body)
                section, problem = find_section(sections, anchor)
                item["anchor"] = anchor
                if section is None:
                    item["state"] = "missing_anchor"
                    item["anchor_problem"] = problem
                else:
                    item["anchor_kind"] = section.anchor_kind
                    item["stable"] = section.stable
                    item["line_start"] = section.line_start
                    item["line_end"] = section.line_end
        else:
            item["authority"] = "document"
    elif candidate.is_relative_to(config.reference_root):
        item["authority"] = "reference"
        item["kind"] = "reference"
    else:
        item["authority"] = "file"
    if "state" not in item:
        item["state"] = "ok"
    return item


def _verification_state(config: ProjectConfig, directory: Path, stage: str) -> tuple[dict[str, Any] | None, str]:
    artifact = directory / stage / "verification.json"
    if not artifact.is_file():
        return None, _relative(artifact, config)
    try:
        data = json.loads(artifact.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None, _relative(artifact, config)
    return (data if isinstance(data, dict) else None), _relative(artifact, config)


def _case_item(
    config: ProjectConfig, task: dict[str, Any], directory: Path, stage: str, case_id: str,
) -> tuple[dict[str, Any], bool]:
    verification, verification_path = _verification_state(config, directory, stage)
    item: dict[str, Any] = {
        "kind": "case",
        "ref": case_id,
        "declared_by": [verification_path],
        "reason": f"requested case {case_id}",
        "state": "ok",
    }
    complete = True
    if verification is None:
        item.update(state="missing", problem="verification.json not found or unreadable")
        return item, False
    planned = verification.get("planned_checks")
    planned = planned if isinstance(planned, list) else []
    match = next((entry for entry in planned
                  if isinstance(entry, dict) and entry.get("id") == case_id), None)
    if match is None:
        item.update(state="missing", problem="case is not planned in verification.json")
        complete = False
    else:
        if isinstance(match.get("expected"), str):
            item["expected"] = match["expected"]
        covers = match.get("covers")
        if isinstance(covers, list):
            item["covers"] = [value for value in covers if isinstance(value, str)]

    criteria = task.get("acceptance_criteria")
    criteria = criteria if isinstance(criteria, list) else []
    ac_text = {}
    for value in criteria:
        if isinstance(value, str):
            match_ac = re.match(r"^(AC-[A-Za-z0-9]+)\s*:\s*(.*)$", value)
            if match_ac:
                ac_text[match_ac.group(1)] = match_ac.group(2)
    if item.get("covers"):
        item["acceptance"] = {
            ac: ac_text.get(ac, "NOT DECLARED IN task.json") for ac in item["covers"]
        }

    checks = verification.get("checks")
    checks = checks if isinstance(checks, list) else []
    latest = None
    for check in checks:
        if not isinstance(check, dict):
            continue
        cases = check.get("cases")
        if isinstance(cases, list) and case_id in cases:
            latest = check
    evidence: dict[str, Any] = {"state": "not_run"}
    if latest is not None:
        exit_code = latest.get("exit_code")
        evidence = {
            "state": "passed" if exit_code == 0 else "failed",
            "exit_code": exit_code,
            "command": latest.get("command"),
            "result": latest.get("result"),
        }
    checked_revision = verification.get("checked_revision")
    if checked_revision is not None:
        evidence["checked_revision"] = checked_revision
    snapshot = verification.get("snapshot_files")
    if isinstance(snapshot, list) and snapshot:
        stale = []
        for entry in snapshot:
            if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                continue
            target = (config.root / entry["path"]).resolve()
            try:
                target.relative_to(config.root.resolve())
            except ValueError:
                stale.append(entry["path"])
                continue
            try:
                current = sha256_file(target) if target.is_file() else None
            except OSError:
                current = None
            if current != entry.get("sha256"):
                stale.append(entry["path"])
        evidence["snapshot_state"] = "stale" if stale else "current"
        if stale:
            evidence["stale_files"] = stale
    else:
        evidence["snapshot_state"] = "unknown"
    item["evidence"] = evidence
    if evidence["state"] == "not_run":
        if item.get("state") == "ok":
            item["state"] = "not_run"
    elif evidence["state"] == "failed":
        item["state"] = "failed"
    return item, complete


def _payload_bytes(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False).encode("utf-8"))


def _trim_to_budget(data: dict[str, Any], max_bytes: int) -> dict[str, Any]:
    if _payload_bytes(data) <= max_bytes:
        data["complete"] = data.get("complete", True) and not data.get("omitted")
        return data
    data["complete"] = False
    optional = ("summary", "expected", "acceptance", "result", "title")
    omitted: list[str] = []
    for item in data.get("items", []):
        for field in optional:
            if field in item and _payload_bytes(data) > max_bytes:
                item.pop(field, None)
                omitted.append(f"{item.get('kind')}:{item.get('ref')}:{field}")
    while data.get("items") and _payload_bytes(data) > max_bytes:
        dropped = data["items"].pop()
        omitted.append(f"item:{dropped.get('kind')}:{dropped.get('ref')}")
    if omitted:
        data["omitted"] = omitted
    return data


def _snapshot_items(previous: Any) -> tuple[dict[str, dict[str, Any]], str | None]:
    if isinstance(previous, dict) and isinstance(previous.get("data"), dict):
        previous = previous["data"]
    if not isinstance(previous, dict):
        return {}, "snapshot must be a JSON object"
    items = previous.get("items")
    if not isinstance(items, list):
        return {}, "snapshot must contain a data.items array"
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        kind = item.get("kind")
        ref = item.get("ref")
        if not isinstance(kind, str) or not isinstance(ref, str):
            continue
        digest = item.get("sha256")
        if not isinstance(digest, str):
            digest = sha256_text(json.dumps(item, ensure_ascii=False, sort_keys=True))
        result[f"{kind}:{ref}"] = {"sha256": digest}
    return result, None


def context(
    store: ArchitectureStore,
    task_key: str,
    *,
    case_id: str | None = None,
    max_bytes: int = DEFAULT_CONTEXT_BYTES,
    since_snapshot: Path | None = None,
) -> dict[str, Any]:
    if max_bytes <= 0:
        raise DocOpsError("ARGS", "--max-bytes must be positive", field="max_bytes", exit_code=2)
    config = store.project_config
    try:
        directory, task_path = task_or_subtask_paths(config, task_key)
    except Exception as exc:  # noqa: BLE001 - task_ops raises its own structured error
        raise DocOpsError("ARGS", str(exc), field="task", exit_code=2) from exc
    if not task_path.is_file():
        raise DocOpsError(
            "TASK-NOT-FOUND", f"task.json not found for {task_key}",
            field="task", suggestion=f"create it: arch task init {task_key}", exit_code=1,
        )
    try:
        task = json.loads(task_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DocOpsError("INVALID", f"cannot read {task_key} task.json: {exc}", exit_code=1) from exc
    if not isinstance(task, dict):
        raise DocOpsError("INVALID", f"{task_key} task.json must be an object", exit_code=1)

    docs = _load_documents(store)
    docs_by_id = {
        doc.metadata["id"]: doc for doc in docs
        if isinstance(doc.metadata.get("id"), str)
    }
    items: list[dict[str, Any]] = []
    complete = True
    omitted: list[str] = []
    notes: list[str] = []

    related_docs = task.get("related_docs")
    related_docs = related_docs if isinstance(related_docs, list) else []
    for ref in related_docs:
        if not isinstance(ref, str):
            continue
        if ref in docs_by_id:
            items.append(_doc_item(docs_by_id[ref], ref, ["related_docs"], config))
        else:
            items.append({
                "kind": "document", "ref": ref, "declared_by": ["related_docs"],
                "reason": "declared in related_docs", "state": "missing",
                "problem": "document id not found",
            })
            complete = False

    context_refs = task.get("project_context_refs")
    context_refs = context_refs if isinstance(context_refs, list) else []
    for ref in context_refs:
        if not isinstance(ref, str) or not ref.strip():
            continue
        item = _path_item(config, ref, ["project_context_refs"], docs_by_id)
        items.append(item)
        if item.get("state") in {"missing", "missing_anchor"}:
            complete = False

    tests = task.get("related_tests")
    tests = tests if isinstance(tests, list) else []
    for entry in tests:
        if not isinstance(entry, dict):
            continue
        location = entry.get("location")
        item = {
            "kind": "test",
            "ref": entry.get("test_id") or location,
            "declared_by": ["related_tests"],
            "reason": "declared in related_tests",
            "command": entry.get("command"),
        }
        if isinstance(location, str) and location:
            target = (config.root / location).resolve()
            item["path"] = location
            try:
                target.relative_to(config.root.resolve())
            except ValueError:
                item.update(state="missing", problem="path escapes the project root")
                complete = False
            else:
                if target.is_file():
                    item["sha256"] = sha256_file(target)
                    item["state"] = "ok"
                else:
                    item.update(state="missing", problem="file not found")
                    complete = False
        else:
            item["state"] = "ok"
        items.append(item)

    stage = current_stage(list_stages(directory))
    case_state: dict[str, Any] | None = None
    if case_id:
        if stage is None:
            case_state = {
                "kind": "case", "ref": case_id, "declared_by": [],
                "reason": f"requested case {case_id}", "state": "missing",
                "problem": "no stage directory",
            }
            complete = False
        else:
            case_state, case_complete = _case_item(config, task, directory, stage, case_id)
            complete = complete and case_complete
        items.append(case_state)

    merged: dict[str, dict[str, Any]] = {}
    for item in items:
        kind = str(item.get("kind"))
        doc_id = item.get("doc_id")
        path = item.get("path")
        if kind in {"document", "file", "reference"} and (doc_id or path):
            key = f"doc:{doc_id}" if doc_id else f"path:{path}"
        else:
            key = f"{kind}:{item.get('ref')}"
        if key not in merged:
            merged[key] = dict(item)
            continue
        existing = merged[key]
        declared = set(existing.get("declared_by") or []) | set(item.get("declared_by") or [])
        existing["declared_by"] = sorted(declared)
        existing["reason"] = f"declared in {', '.join(sorted(declared))}"
        for field, value in item.items():
            existing.setdefault(field, value)
        if item.get("state") in {"missing", "missing_anchor", "superseded"}:
            existing["state"] = item["state"]
    items = list(merged.values())

    for item in items:
        if item.get("state") in {"superseded", "missing_anchor"}:
            complete = False
        if item.get("kind") == "document" and item.get("status") in ARCHIVED_STATUSES:
            complete = False

    data: dict[str, Any] = {
        "task_key": task_key,
        "stage": stage,
        "case": case_id,
        "max_bytes": max_bytes,
        "items": items,
        "complete": complete,
        "notes": notes,
    }

    if since_snapshot is not None:
        try:
            previous = json.loads(since_snapshot.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DocOpsError(
                "ARGS", f"cannot read snapshot {since_snapshot}: {exc}",
                field="since_snapshot", exit_code=2,
            ) from exc
        previous_items, problem = _snapshot_items(previous)
        if problem:
            raise DocOpsError(
                "ARGS", f"invalid snapshot: {problem}",
                field="since_snapshot", exit_code=2,
            )
        current = {}
        for item in items:
            digest = item.get("sha256")
            if not isinstance(digest, str):
                digest = sha256_text(json.dumps(item, ensure_ascii=False, sort_keys=True))
            current[f"{item.get('kind')}:{item.get('ref')}"] = {"sha256": digest, "item": item}
        added = sorted(key for key in current if key not in previous_items)
        removed = sorted(key for key in previous_items if key not in current)
        changed = sorted(
            key for key in current
            if key in previous_items and previous_items[key]["sha256"] != current[key]["sha256"]
        )
        data["delta"] = {
            "added": added,
            "changed": changed,
            "removed": removed,
            "unchanged_count": len(current) - len(added) - len(changed),
        }
        data["items"] = [current[key]["item"] for key in (*added, *changed)]

    data = _trim_to_budget(data, max_bytes)
    if data.get("omitted"):
        omitted = list(data["omitted"])
        data["notes"].append(
            "output trimmed to --max-bytes; omitted entries: " + ", ".join(omitted)
        )
        data["complete"] = False
    return data


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), "-c", "core.quotePath=false", *args],
        capture_output=True, text=True, errors="replace", check=False,
    )


def _git_prefix(root: Path) -> str:
    result = _git(root, "rev-parse", "--show-prefix")
    return result.stdout.strip() if result.returncode == 0 else ""


def _git_show(root: Path, base: str, relative: str) -> str | None:
    result = _git(root, "show", f"{base}:{_git_prefix(root)}{relative}")
    return result.stdout if result.returncode == 0 else None


def _metadata_id(text: str) -> str | None:
    frontmatter, _, _ = split_frontmatter(text)
    if not frontmatter:
        return None
    try:
        metadata = yaml.load(frontmatter, Loader=UniqueKeyLoader)
    except yaml.YAMLError:
        return None
    if not isinstance(metadata, dict):
        return None
    value = metadata.get("id")
    return value if isinstance(value, str) else None


def _task_records(config: ProjectConfig) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    tasks_root = config.tasks_root
    if not tasks_root.is_dir():
        return records
    for directory in sorted(tasks_root.iterdir()):
        if not directory.is_dir():
            continue
        candidates = [(directory.name, directory / "task.json")]
        subtasks = directory / "subtasks"
        if subtasks.is_dir():
            for child in sorted(subtasks.iterdir()):
                if child.is_dir():
                    candidates.append((f"{directory.name}-{child.name}", child / "task.json"))
        for key, path in candidates:
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(data, dict):
                records.append({"key": key, "path": path, "data": data})
    return records


def _section_changes(base_body: str | None, current_body: str | None) -> dict[str, Any]:
    base_sections, base_duplicates = section_map(base_body or "")
    current_sections, current_duplicates = section_map(current_body or "")
    added, changed, removed = [], [], []
    for key in sorted(current_sections):
        section = current_sections[key]
        record = {
            "anchor": section.anchor,
            "anchor_kind": section.anchor_kind,
            "stable": section.stable,
            "title": section.title,
            "line_start": section.line_start,
        }
        if key not in base_sections:
            added.append(record)
        elif sha256_text(base_sections[key].text) != sha256_text(section.text):
            record["previous_line_start"] = base_sections[key].line_start
            changed.append(record)
    for key in sorted(base_sections):
        if key not in current_sections:
            section = base_sections[key]
            removed.append({
                "anchor": section.anchor,
                "anchor_kind": section.anchor_kind,
                "stable": section.stable,
                "title": section.title,
                "line_start": section.line_start,
            })
    unchanged = len(set(base_sections) & set(current_sections)) - len(changed)
    return {
        "added": added,
        "changed": changed,
        "removed": removed,
        "unchanged_count": max(0, unchanged),
        "duplicate_anchors": sorted(set(base_duplicates) | set(current_duplicates)),
    }


def impact(store: ArchitectureStore, base: str, *, scope: str = "docs") -> dict[str, Any]:
    config = store.project_config
    root = config.root
    inside = _git(root, "rev-parse", "--is-inside-work-tree")
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        raise DocOpsError(
            "ARGS", "impact requires a Git work tree",
            field="since", exit_code=2,
        )
    valid = _git(root, "cat-file", "-e", f"{base}^{{commit}}")
    if valid.returncode != 0:
        raise DocOpsError(
            "ARGS", f"unknown Git revision {base!r}",
            field="since", suggestion="pass an existing commit, tag or branch", exit_code=2,
        )
    if scope not in {"docs", "all"}:
        raise DocOpsError("ARGS", f"unknown scope {scope!r}", field="scope", exit_code=2)

    diff = _git(root, "diff", "--name-status", "--relative", base, "--")
    if diff.returncode != 0:
        raise DocOpsError("GIT", diff.stderr.strip() or "git diff failed", exit_code=2)
    status_by_path: dict[str, str] = {}
    for line in diff.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, path = parts[0], parts[-1]
        status_by_path[path] = {"A": "added", "D": "deleted", "M": "modified", "R": "modified"}.get(
            status[0], "modified"
        )
    untracked = _git(root, "ls-files", "--others", "--exclude-standard")
    untracked_paths = set(untracked.stdout.splitlines())
    for path in untracked_paths:
        status_by_path.setdefault(path, "added")

    docs = _load_documents(store)
    docs_by_path = {_relative(doc.path, config): doc for doc in docs}
    architecture_root = config.architecture_root.resolve()
    if scope == "docs":
        status_by_path = {
            path: status for path, status in status_by_path.items()
            if path.endswith(".md") and (root / path).resolve().is_relative_to(architecture_root)
        }
        untracked_paths = {path for path in untracked_paths if path in status_by_path}

    changed_files: list[dict[str, Any]] = []
    changed_sections: list[dict[str, Any]] = []
    changed_doc_ids: list[str] = []
    for relative in sorted(status_by_path):
        path = (root / relative).resolve()
        status = status_by_path[relative]
        current_text: str | None = None
        if status != "deleted" and path.is_file():
            try:
                current_text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                current_text = None
        base_text = None if status == "added" else _git_show(root, base, relative)
        current_id = _metadata_id(current_text) if current_text is not None else None
        base_id = _metadata_id(base_text) if base_text is not None else None
        doc_id = current_id or base_id
        record: dict[str, Any] = {
            "path": relative,
            "status": status,
            "doc_id": doc_id,
            "tracked": relative not in untracked_paths,
        }
        changed_files.append(record)
        if doc_id:
            changed_doc_ids.append(doc_id)
        if path.is_relative_to(architecture_root) and relative.endswith(".md"):
            _, base_body, _ = split_frontmatter(base_text or "")
            _, current_body, _ = split_frontmatter(current_text or "")
            sections = _section_changes(base_body, current_body)
            sections.update({"path": relative, "doc_id": doc_id})
            changed_sections.append(sections)

    tasks = _task_records(config)
    affected: list[dict[str, Any]] = []
    path_to_doc_id = {
        item["path"]: item["doc_id"] for item in changed_files if item.get("doc_id")
    }
    consumed: set[str] = set()

    def add_affected(kind: str, identifier: str, path: str, via: str, anchor: str | None = None):
        entry = {"kind": kind, "id": identifier, "path": path, "via": via}
        if anchor:
            entry["anchor"] = anchor
        if entry not in affected:
            affected.append(entry)

    changed_paths = set(status_by_path)
    for doc in docs:
        doc_path = _relative(doc.path, config)
        related = doc.metadata.get("related")
        related = related if isinstance(related, list) else []
        for doc_id in changed_doc_ids:
            if doc_id in related:
                consumed.add(doc_id)
                add_affected("document", str(doc.metadata.get("id")), doc_path, "related")
        for line_no, target in _scan_links(doc.path, doc.body):
            parsed = urlparse(target)
            if parsed.scheme in {"http", "https", "mailto", "tel"}:
                continue
            path_part, _, anchor = target.partition("#")
            path_part = path_part.split("?", 1)[0]
            if not path_part:
                continue
            candidate = (doc.path.parent / path_part).resolve()
            try:
                relative = candidate.relative_to(root).as_posix()
            except ValueError:
                continue
            if relative in changed_paths:
                if path_to_doc_id.get(relative):
                    consumed.add(path_to_doc_id[relative])
                add_affected(
                    "document", str(doc.metadata.get("id")), doc_path, "link", anchor or None,
                )

    for record in tasks:
        data = record["data"]
        related_docs = data.get("related_docs")
        related_docs = related_docs if isinstance(related_docs, list) else []
        for doc_id in changed_doc_ids:
            if doc_id in related_docs:
                consumed.add(doc_id)
                add_affected("task", record["key"], _relative(record["path"], config), "related_docs")
        refs = data.get("project_context_refs")
        refs = refs if isinstance(refs, list) else []
        for ref in refs:
            if not isinstance(ref, str):
                continue
            path_part = ref.partition("#")[0]
            if path_part in changed_paths or ref.partition("#")[0] in changed_paths:
                if path_to_doc_id.get(path_part):
                    consumed.add(path_to_doc_id[path_part])
                add_affected(
                    "task", record["key"], _relative(record["path"], config),
                    "project_context_refs", ref.partition("#")[2] or None,
                )

    affected.sort(key=lambda item: (item["kind"], item["id"], item["via"]))
    unverified = sorted(doc_id for doc_id in set(changed_doc_ids) if doc_id not in consumed)
    notes = [
        "impact follows declared links only; textual similarity is never reported as proven impact",
        "untracked files are treated as added sections; Git rename detection is not performed",
    ]
    if not changed_files:
        notes.append(f"no changes between {base} and the working tree")
    return {
        "base": base,
        "scope": scope,
        "changed_files": changed_files,
        "changed_sections": changed_sections,
        "affected": affected,
        "unverified_coverage": unverified,
        "notes": notes,
    }
