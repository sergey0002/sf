#!/usr/bin/env python3
"""Build or check the Obsidian/agent index (Индекс.md) for /home/user/sf/arenaauditplan."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "Индекс.md"
SKIP_DIRS = {".git", ".obsidian", "scripts", "__pycache__", "Unselected files"}


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    raw = text[4:end]
    out: dict[str, str] = {}
    for key in ("id", "title", "description", "status", "track", "stage"):
        m = re.search(rf"^{re.escape(key)}:\s*(.*)$", raw, flags=re.M)
        if m:
            val = m.group(1).strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                val = val[1:-1]
            out[key] = val
    return out


def make_index() -> str:
    pages: list[tuple[str, str, str, str, str]] = []
    for path in sorted(ROOT.rglob("*.md")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.resolve() == INDEX.resolve():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        fm = parse_frontmatter(text)
        h1 = re.search(r"^#\s+(.+?)\s*$", text, flags=re.M)
        title = fm.get("title") or (h1.group(1) if h1 else path.stem)
        desc = fm.get("description", "")
        doc_id = fm.get("id", "AAP-AGENTS" if path.name == "AGENTS.md" else "")
        if path.name == "AGENTS.md":
            title = "AGENTS.md — правила поддержки хранилища, SSOT и приёма обзоров"
            desc = (
                "Загружайте перед любым редактированием arenaauditplan, приёмом нового "
                "экспертного обзора, проверкой конфликтов или генерацией задач task.json."
            )
        rel = path.relative_to(ROOT).as_posix()
        group = path.parent.relative_to(ROOT).as_posix()
        group_label = "00-Корень-и-навигация" if group == "." else group
        pages.append((group_label, rel, doc_id, title, desc))

    pages.sort(key=lambda item: (item[0].casefold(), item[1].casefold()))
    grouped: dict[str, list[tuple[str, str, str, str]]] = {}
    for grp, rel, doc_id, title, desc in pages:
        grouped.setdefault(grp, []).append((rel, doc_id, title, desc))

    lines = [
        "---",
        'id: "AAP-INDEX"',
        'title: "Индекс хранилища arenaauditplan"',
        'description: "Загружайте первым для точной маршрутизации агента по всем тематическим и этапным файлам без чтения всего хранилища."',
        'status: "index"',
        'track: "both"',
        'stage: "all"',
        "paths: []",
        "tags: [moc, индекс, навигация, agents]",
        'aliases: ["Индекс", "Index", "Каталог arenaauditplan"]',
        "---",
        "",
        "# Индекс хранилища `arenaauditplan`",
        "",
        "> [!abstract] Как пользоваться (Index-First)",
        "> Полный машинно-проверяемый каталог всех заметок хранилища. Сначала прочитайте этот индекс, выберите только релевантные задаче файлы по полю триггера после тире и откройте их. Тематическая карта — [[Главная]], правила работы и приёма новых экспертных обзоров — [[AGENTS.md]], проверка непротиворечивости — [[06-Консилиум-и-конфликты/Реестр-конфликтов-и-решений]].",
        "",
        "## Каталог разделов и заметок",
        "",
    ]

    for grp, items in grouped.items():
        lines.append(f"### {grp}")
        lines.append("")
        for rel, doc_id, title, desc in items:
            badge = f"`{doc_id}` · " if doc_id else ""
            lines.append(f"- {badge}[{title}](<{rel}>) — {desc}")
        lines.append("")

    lines += [
        "## Автоматические проверки хранилища",
        "",
        "- Пересборка индекса: `python3 data/arenaauditplan-encyclopedia/scripts/build_index.py`",
        "- Проверка актуальности индекса: `python3 data/arenaauditplan-encyclopedia/scripts/build_index.py --check`",
        "- Полный аудит ссылок, метаданных, дублирования и внутренних конфликтов: `python3 data/arenaauditplan-encyclopedia/scripts/lint_wiki.py`",
        "",
        "## Связи",
        "",
        "- [[Главная]] · [[Глоссарий]] · [[Справочник артефактов, команд и схем]] · [[Журнал]] · [[AGENTS.md]] · [[06-Консилиум-и-конфликты/Реестр-конфликтов-и-решений]]",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="exit 1 if Индекс.md is stale")
    args = parser.parse_args()
    expected = make_index()
    if args.check:
        actual = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
        if actual != expected:
            print("FAIL: Индекс.md устарел. Запустите: python3 data/arenaauditplan-encyclopedia/scripts/build_index.py")
            return 1
        print("OK: Индекс.md полностью актуален.")
        return 0
    INDEX.write_text(expected, encoding="utf-8")
    print(f"OK: Обновлён {INDEX.relative_to(ROOT)} ({len(expected.splitlines())} строк)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
