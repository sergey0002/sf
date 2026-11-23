#!/usr/bin/env python3
"""Lint the Obsidian vault /home/user/sf/arenaauditplan for links, SSOT, duplicates, and conflicts."""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = ROOT.parents[1]
SKIP_DIRS = {".git", ".obsidian", "scripts", "__pycache__", "Unselected files"}
REQUIRED_FM_KEYS = ("id", "title", "description", "status", "track", "stage", "paths", "tags", "aliases")


def notes() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*.md") if not any(part in SKIP_DIRS for part in p.parts))


def fm_block(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    return text[4:end]


def strip_code(text: str) -> str:
    no_fences = re.sub(r"```.*?```|~~~.*?~~~", "", text, flags=re.S)
    return re.sub(r"`[^`]*`", "", no_fences)


def parse_aliases(fm: str | None) -> list[str]:
    if not fm:
        return []
    m = re.search(r"^aliases:\s*\[(.*?)\]\s*$", fm, flags=re.M)
    if not m:
        return []
    return [x.strip().strip("\"'") for x in re.split(r",\s*", m.group(1)) if x.strip()]


def main() -> int:
    all_notes = notes()
    by_stem: dict[str, Path] = {}
    by_id: dict[str, Path] = {}
    alias_to_path: dict[str, Path] = {}
    errors: list[str] = []
    warnings: list[str] = []
    outgoing: Counter[Path] = Counter()
    incoming: Counter[Path] = Counter()

    # Track SSOT definitions to prevent duplication across notes
    prob_defs: dict[str, list[Path]] = {}
    conf_defs: dict[str, list[Path]] = {}
    task_defs: dict[str, list[Path]] = {}

    for path in all_notes:
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8", errors="replace")
        stem = path.stem
        if stem in by_stem:
            errors.append(f"Duplicate note filename stem {stem!r}: {by_stem[stem].relative_to(ROOT)} vs {rel}")
        else:
            by_stem[stem] = path

        fm = fm_block(text)
        status_val = ""
        if path.name != "AGENTS.md":
            if fm is None:
                errors.append(f"{rel}: missing or unclosed YAML frontmatter")
            else:
                for key in REQUIRED_FM_KEYS:
                    if not re.search(rf"^{key}:\s*.+$", fm, flags=re.M):
                        errors.append(f"{rel}: frontmatter missing required key '{key}'")
                m_id = re.search(r'^id:\s*["\']?([^"\'\n]+)["\']?\s*$', fm, flags=re.M)
                if m_id:
                    doc_id = m_id.group(1).strip()
                    if doc_id in by_id:
                        errors.append(f"Duplicate frontmatter id {doc_id!r}: {by_id[doc_id].relative_to(ROOT)} vs {rel}")
                    else:
                        by_id[doc_id] = path
                m_st = re.search(r'^status:\s*["\']?([^"\'\n]+)["\']?\s*$', fm, flags=re.M)
                if m_st:
                    status_val = m_st.group(1).strip()
                m_paths = re.search(r"^paths:\s*\[(.*?)\]\s*$", fm, flags=re.M)
                if m_paths and m_paths.group(1).strip():
                    for item in re.split(r",\s*", m_paths.group(1)):
                        p_str = item.strip().strip("\"'")
                        if p_str and not (REPO_ROOT / p_str).exists():
                            errors.append(f"{rel}: frontmatter path does not exist in repo: {p_str!r}")

        visible = strip_code(text)
        h1 = re.findall(r"^#\s+.+$", visible, flags=re.M)
        if len(h1) != 1:
            errors.append(f"{rel}: expected exactly 1 H1 outside code blocks, found {len(h1)}")

        for alias in parse_aliases(fm):
            if alias in alias_to_path and alias_to_path[alias] != path:
                warnings.append(f"Alias collision {alias!r}: {alias_to_path[alias].relative_to(ROOT)} / {rel}")
            else:
                alias_to_path[alias] = path

        # Check SSOT row/heading definitions
        for m in re.finditer(r"^\|\s*\*\*`(PROB-\d{2})`\*\*", text, flags=re.M):
            prob_defs.setdefault(m.group(1), []).append(path)
        for m in re.finditer(r"^###\s+(CONF-\d{2})\b", text, flags=re.M):
            conf_defs.setdefault(m.group(1), []).append(path)
        for m in re.finditer(r"^###\s+(TASK-F\d{1,2}-\d{2})\b", text, flags=re.M):
            task_defs.setdefault(m.group(1), []).append(path)

        # Conflict recurrence guard: superseded custom MCP driver must not appear as active driver in canonical notes
        if status_val == "canonical" and "driver: mcp-context-kernel" in text:
            errors.append(f"{rel}: superseded 'driver: mcp-context-kernel' found in canonical note (violates CONF-01)")
        if "/home/user/" in visible and path.name != "AGENTS.md":
            errors.append(f"{rel}: hardcoded '/home/user/' path outside code spans/fences")

    for kind, mapping in (("PROB", prob_defs), ("CONF", conf_defs), ("TASK", task_defs)):
        for code, holders in mapping.items():
            uniq_holders = sorted(set(holders))
            if len(uniq_holders) > 1:
                errors.append(
                    f"SSOT duplication of {code} definition across multiple files: "
                    + ", ".join(str(p.relative_to(ROOT)) for p in uniq_holders)
                )

    def resolve_wikilink(target: str) -> Path | None:
        target = target.strip()
        if not target:
            return None
        if target in by_stem:
            return by_stem[target].resolve()
        candidate = ROOT / target
        if candidate.suffix.lower() != ".md":
            candidate = candidate.with_suffix(".md")
        if candidate.exists():
            return candidate.resolve()
        stem = Path(target).stem
        return (by_stem.get(stem) or alias_to_path.get(target))

    for path in all_notes:
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8", errors="replace")
        visible = strip_code(text)
        for raw in re.findall(r"\[\[([^\]]+)\]\]", visible):
            target = raw.replace("\\|", "|").split("|", 1)[0].split("#", 1)[0].strip()
            if not target:
                continue
            resolved = resolve_wikilink(target)
            if resolved is None:
                errors.append(f"{rel}: broken wikilink [[{raw}]]")
                continue
            if resolved.resolve() != path.resolve():
                outgoing[path] += 1
                incoming[resolved.resolve()] += 1

        md_links = re.findall(r"(?<!!)\[[^\]]+\]\(<([^>]+)>\)|(?<!!)\[[^\]]+\]\(([^)]+)\)", visible)
        for g1, g2 in md_links:
            raw = (g1 or g2).strip().strip("<>")
            if not raw or re.match(r"^(?:https?:|mailto:|data:|#)", raw, flags=re.I):
                continue
            filepart = unquote(raw.split("#", 1)[0].split("?", 1)[0])
            if not filepart:
                continue
            target_path = (path.parent / filepart).resolve()
            if not target_path.exists():
                errors.append(f"{rel}: broken relative Markdown link ({raw}) -> {target_path}")
            elif target_path.suffix.lower() == ".md" and ROOT.resolve() in target_path.parents:
                if target_path != path.resolve():
                    outgoing[path] += 1
                    incoming[target_path] += 1

    for path in all_notes:
        if path.name in {"Индекс.md", "AGENTS.md"}:
            continue
        if incoming[path.resolve()] == 0:
            errors.append(f"Orphan note (0 inbound links): {path.relative_to(ROOT)}")

    index_path = ROOT / "Индекс.md"
    if not index_path.exists():
        errors.append("Missing Индекс.md (run build_index.py)")
    else:
        idx_text = index_path.read_text(encoding="utf-8", errors="replace")
        for path in all_notes:
            if path.resolve() == index_path.resolve():
                continue
            rel_posix = path.relative_to(ROOT).as_posix()
            if rel_posix not in idx_text:
                errors.append(f"Индекс.md missing entry for {rel_posix}")

    print(
        f"Vault check: {len(all_notes)} notes | {sum(outgoing.values())} internal links | "
        f"{len(prob_defs)} PROB | {len(conf_defs)} CONF | {len(task_defs)} TASK specs"
    )
    for w in warnings:
        print("WARN:", w)
    if errors:
        print(f"FAILED with {len(errors)} error(s):")
        for e in errors:
            print("ERROR:", e)
        return 1
    print("OK: 0 broken links, 0 orphans, 0 duplicate SSOT definitions, 0 active conflict regressions.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
