#!/usr/bin/env python3
"""Lint an Obsidian/agent documentation vault using only Python's stdlib."""
from __future__ import annotations
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", ".obsidian", "node_modules", "Unselected files", "build", "dist"}


def notes() -> list[Path]:
    return sorted(p for p in ROOT.rglob("*.md") if not any(part in SKIP_DIRS for part in p.parts))


def fm_block(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    return text[4:end]


def aliases(fm: str | None) -> list[str]:
    if not fm:
        return []
    m = re.search(r"^aliases:\s*\[(.*?)\]\s*$", fm, re.M)
    if not m:
        return []
    return [x.strip().strip("\"'") for x in re.split(r",\s*", m.group(1)) if x.strip()]


def main() -> int:
    all_notes = notes()
    by_stem: dict[str, Path] = {}
    duplicate_stems: dict[str, list[Path]] = {}
    alias_to_path: dict[str, Path] = {}
    errors: list[str] = []
    warnings: list[str] = []
    outgoing: Counter[Path] = Counter()
    incoming: Counter[Path] = Counter()

    for path in all_notes:
        text = path.read_text(encoding="utf-8", errors="replace")
        stem = path.stem
        if stem in by_stem:
            duplicate_stems.setdefault(stem, [by_stem[stem]]).append(path)
        else:
            by_stem[stem] = path
        fm = fm_block(text)
        if path.name != "AGENTS.md":
            if fm is None:
                errors.append(f"{path.relative_to(ROOT)}: отсутствует/не закрыт YAML frontmatter")
            else:
                for key in ("title", "description", "paths", "tags", "aliases"):
                    if not re.search(rf"^{key}:\s*.+$", fm, re.M):
                        errors.append(f"{path.relative_to(ROOT)}: frontmatter: нет {key}")
        visible = re.sub(r"```.*?```|~~~.*?~~~", "", text, flags=re.S)
        visible = re.sub(r"`[^`]*`", "", visible)
        h1 = re.findall(r"^#\s+.+$", visible, re.M)
        if len(h1) != 1:
            errors.append(f"{path.relative_to(ROOT)}: ожидается ровно один H1 вне code fences, найдено {len(h1)}")
        for alias in aliases(fm):
            if alias in alias_to_path and alias_to_path[alias] != path:
                warnings.append(f"Alias collision {alias!r}: {alias_to_path[alias].relative_to(ROOT)} / {path.relative_to(ROOT)}")
            else:
                alias_to_path[alias] = path

    for dup, paths in duplicate_stems.items():
        warnings.append(f"Неуникальное имя заметки {dup!r}: {', '.join(str(p.relative_to(ROOT)) for p in paths)}")

    def resolve_target(target: str) -> Path | None:
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
        return by_stem.get(stem) or alias_to_path.get(target)

    for path in all_notes:
        text = path.read_text(encoding="utf-8", errors="replace")
        visible = re.sub(r"```.*?```|~~~.*?~~~", "", text, flags=re.S)
        visible = re.sub(r"`[^`]*`", "", visible)
        for raw in re.findall(r"\[\[([^\]]+)\]\]", visible):
            target = raw.split("|", 1)[0].split("#", 1)[0].strip()
            resolved = resolve_target(target)
            if resolved is None:
                errors.append(f"{path.relative_to(ROOT)}: broken wikilink [[{raw}]]")
                continue
            if resolved != path.resolve():
                outgoing[path] += 1
                incoming[resolved] += 1
        # Markdown links: external URLs/mailto/data are ignored; local files resolve relative to source.
        # Angle-bracket destinations are parsed first so spaces/parentheses in Obsidian filenames work.
        md_links = re.findall(r"(?<!!)\[[^\]]+\]\(<([^>]+)>\)|(?<!!)\[[^\]]+\]\(([^)]+)\)", visible)
        for groups in md_links:
            raw = (groups[0] or groups[1]).strip().strip("<>")
            if not raw or re.match(r"^(?:https?:|mailto:|data:|#)", raw, re.I):
                continue
            filepart = unquote(raw.split("#", 1)[0].split("?", 1)[0])
            if not filepart:
                continue
            target_path = (path.parent / filepart).resolve()
            if not target_path.exists():
                errors.append(f"{path.relative_to(ROOT)}: broken relative Markdown link ({raw})")
            elif target_path.suffix.lower() == ".md" and target_path != path.resolve():
                outgoing[path] += 1
                incoming[target_path] += 1

    # Markdown notes should be reachable from the wiki graph; AGENTS is intentionally an instruction root.
    for path in all_notes:
        if path.name in {"Индекс.md", "AGENTS.md"}:
            continue
        if incoming[path.resolve()] == 0:
            warnings.append(f"Orphan note (no inbound links): {path.relative_to(ROOT)}")

    index_path = ROOT / "Индекс.md"
    if not index_path.exists():
        errors.append("Нет Индекс.md")
    else:
        idx_text = index_path.read_text(encoding="utf-8", errors="replace")
        for path in all_notes:
            if path.resolve() in {index_path.resolve()}:
                continue
            rel = path.relative_to(ROOT).as_posix()
            # Relative markdown links may be angle-bracket wrapped; also allow explicit Obsidian wikilinks.
            if rel not in idx_text and path.stem not in idx_text:
                errors.append(f"Индекс.md: отсутствует запись о {rel}")

    print(f"Vault: {len(all_notes)} Markdown files; {sum(outgoing.values())} resolved internal links")
    if warnings:
        print(f"Warnings: {len(warnings)}")
        for item in warnings:
            print("WARN:", item)
    if errors:
        print(f"Errors: {len(errors)}")
        for item in errors:
            print("ERROR:", item)
        return 1
    print("OK: frontmatter, H1, wikilinks, relative Markdown links, and index coverage.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
