"""Addressable Markdown sections for ``DOC-ID#anchor`` references.

Explicit anchors use the Pandoc/MkDocs ``{#anchor}`` heading suffix. Headings
without an explicit anchor receive a deterministic slug anchor and are marked
as non-stable: they survive content edits but not heading renames.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
_ATX_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
_EXPLICIT_RE = re.compile(r"\s*\{#([A-Za-z0-9][A-Za-z0-9._:-]*)\}\s*$")
_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)


@dataclass(frozen=True)
class Section:
    anchor: str
    anchor_kind: str
    level: int
    title: str
    heading_path: tuple[str, ...]
    line_start: int
    line_end: int
    text: str

    @property
    def stable(self) -> bool:
        return self.anchor_kind == "explicit"

    @property
    def slug(self) -> str:
        return slugify(self.title)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path) -> str:
    return sha256_bytes(path.read_bytes())


def slugify(title: str) -> str:
    value = title.casefold()
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE)
    value = re.sub(r"[\s_-]+", "-", value).strip("-")
    return value or "section"


def split_frontmatter(text: str) -> tuple[str, str, int]:
    """Return ``(frontmatter, body, body_line_offset)`` for Markdown text."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return "", text, 0
    return match.group(1), text[match.end():], text[: match.end()].count("\n")


def parse_sections(body: str) -> list[Section]:
    """Parse ATX headings outside fenced code blocks into ordered sections."""
    lines = body.splitlines()
    headings: list[tuple[int, int, str, str, str]] = []
    fence_char: str | None = None
    fence_len = 0
    for index, line in enumerate(lines, start=1):
        marker = _FENCE_RE.match(line)
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
        match = _ATX_RE.match(line)
        if not match:
            continue
        level = len(match.group(1))
        raw_title = match.group(2).strip()
        explicit = _EXPLICIT_RE.search(raw_title)
        if explicit:
            title = _EXPLICIT_RE.sub("", raw_title).strip()
            anchor, anchor_kind = explicit.group(1), "explicit"
        else:
            title = raw_title
            anchor, anchor_kind = slugify(title), "slug"
        headings.append((index, level, title, anchor, anchor_kind))

    sections: list[Section] = []
    stack: list[tuple[int, str]] = []
    for position, (start, level, title, anchor, anchor_kind) in enumerate(headings):
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        heading_path = tuple(item[1] for item in stack)
        end = len(lines)
        for later_start, later_level, _, _, _ in headings[position + 1:]:
            if later_level <= level:
                end = later_start - 1
                break
        sections.append(Section(
            anchor=anchor,
            anchor_kind=anchor_kind,
            level=level,
            title=title,
            heading_path=heading_path,
            line_start=start,
            line_end=end,
            text="\n".join(lines[start - 1:end]),
        ))
    return sections


def find_section(sections: list[Section], anchor: str) -> tuple[Section | None, str | None]:
    """Resolve an anchor, preferring explicit anchors over generated slugs."""
    explicit = [item for item in sections
                if item.anchor_kind == "explicit" and item.anchor == anchor]
    if len(explicit) == 1:
        return explicit[0], None
    if len(explicit) > 1:
        return None, "ambiguous"
    generated = [item for item in sections if item.slug == anchor]
    if len(generated) == 1:
        return generated[0], None
    if len(generated) > 1:
        return None, "ambiguous"
    return None, "missing"


def anchor_exists(sections: list[Section], anchor: str) -> bool:
    section, _ = find_section(sections, anchor)
    return section is not None


def section_map(body: str) -> tuple[dict[str, Section], list[str]]:
    """Map stable section keys to sections and report duplicate anchors."""
    result: dict[str, Section] = {}
    duplicates: list[str] = []
    for section in parse_sections(body):
        key = section.anchor if section.anchor_kind == "explicit" else f"slug:{section.anchor}"
        if key in result:
            duplicates.append(key)
            continue
        result[key] = section
    return result, duplicates
