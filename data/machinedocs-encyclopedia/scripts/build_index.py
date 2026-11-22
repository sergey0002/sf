#!/usr/bin/env python3
"""Build/check the human- and agent-readable Obsidian Markdown index."""
from __future__ import annotations
import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "Индекс.md"
EXCLUDED = {INDEX.resolve()}


def frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    raw = text[4:end]
    data: dict[str, str] = {}
    for key in ("title", "description", "tags", "aliases", "paths"):
        m = re.search(rf"^{re.escape(key)}:\s*(.*)$", raw, flags=re.M)
        if m:
            data[key] = m.group(1).strip()
    return data


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def make_index() -> str:
    pages = []
    for path in ROOT.rglob("*.md"):
        if path.resolve() == INDEX.resolve() or "Unselected files" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        fm = frontmatter(text)
        h1 = re.search(r"^#\s+(.+?)\s*$", text, flags=re.M)
        title = unquote(fm.get("title", "")) or (h1.group(1) if h1 else path.stem)
        description = unquote(fm.get("description", ""))
        if path.name == "AGENTS.md":
            title = "AGENTS.md — правила поддержки энциклопедии"
            description = "Прочитать перед изменением vault: схема заметок, источники, Obsidian-ссылки, индекс и lint."
        if not description:
            description = "Заметка энциклопедии; выберите её по названию и связям."
        rel = path.relative_to(ROOT).as_posix()
        pages.append((path.parent.relative_to(ROOT).as_posix() or "Корень", title, description, rel))
    pages.sort(key=lambda item: (item[0].casefold(), item[1].casefold()))
    groups: dict[str, list[tuple[str, str, str]]] = {}
    for group, title, description, rel in pages:
        groups.setdefault(group, []).append((title, description, rel))
    out = [
        "---",
        'title: "Индекс энциклопедии"',
        'description: "Загружайте первым для маршрутизации по темам и поиска релевантных заметок в Obsidian vault."',
        "paths: []",
        "tags: [moc, индекс, agents]",
        "aliases: [Index, Индекс знаний]",
        "---",
        "",
        "# Индекс энциклопедии",
        "",
        "> [!abstract] Как пользоваться",
        "> Это полный каталог заметок для человека и агента. Сначала выберите раздел и загрузите только те страницы,",
        "> чьё описание соответствует задаче. Для тематической карты откройте [[Главная]]; для правил редактирования — [[AGENTS.md]].",
        "> Ссылки на файлы ниже — относительные Markdown-ссылки от корня vault; Obsidian показывает backlinks и graph edges.",
        "",
        "## Разделы",
        "",
    ]
    for group, entries in groups.items():
        header = group if group != "." else "Корень"
        out += [f"### {header}", ""]
        for title, description, rel in entries:
            out.append(f"- [{title}](<{rel}>) — {description}")
        out.append("")
    out += [
        "## Поддержка и проверки",
        "",
        "- [[Главная]] — тематическая карта и обзор vault.",
        "- [[Глоссарий]] — определения терминов и сущностей.",
        "- [[Журнал]] — датированные записи об ingest, исследованиях и lint.",
        "- Проверка ссылок/метаданных: `python3 scripts/lint_wiki.py`.",
        "- Проверка актуальности индекса: `python3 scripts/build_index.py --check`.",
        "",
    ]
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if the index is stale")
    args = parser.parse_args()
    expected = make_index()
    if args.check:
        actual = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
        if actual != expected:
            print("Индекс устарел. Запусти: python3 scripts/build_index.py")
            return 1
        print("Индекс актуален.")
        return 0
    INDEX.write_text(expected, encoding="utf-8")
    print(f"Обновлён {INDEX.relative_to(ROOT)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
