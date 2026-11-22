"""Согласованность реестра типов и статусов архитектурных документов.

Оракул проверки — независимые источники, а не один и тот же парсер:
`paths.yaml` объявляет наборы, §5.5 контракта описывает формат каждого типа,
`index.json` показывает фактическое использование, `schemas/bodies/*.json`
задаёт проверяемую структуру тела.
"""

import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PATHS = "doc/config/paths.yaml"
INDEX = "doc/architecture/index.json"
CONTRACT = "doc/architecture/system/architecture-contract.md"
DOC_SCHEMA = "doc/architecture/schemas/document.schema.json"
BODIES = "doc/architecture/schemas/bodies"

ROW_RE = re.compile(r"^\|\s*`([a-z][a-z0-9-]*)`\s*\|(.*)$")


def _project(root):
    data = yaml.safe_load((root / PATHS).read_text(encoding="utf-8"))
    return data["project"]


def _used_types(root):
    documents = json.loads((root / INDEX).read_text(encoding="utf-8"))["documents"]
    return {doc["type"] for doc in documents}


def _contract_text(root):
    return (root / CONTRACT).read_text(encoding="utf-8")


def _registry_rows(text):
    section = text.split("### 5.5", 1)[1].split("\n#### ", 1)[0]
    rows = {}
    for line in section.splitlines():
        match = ROW_RE.match(line)
        if match:
            rows[match.group(1)] = match.group(2)
    return rows


def _contract_statuses(text):
    section = text.split("### 2.3", 1)[1].split("\n---", 1)[0]
    match = re.search(r"`status: ([^`]+)`", section)
    if not match:
        return set()
    return {value.strip() for value in match.group(1).split("|")}


def registry_problems(root):
    """Возвращает список нарушений согласованности для дерева `root`."""
    problems = []
    project = _project(root)
    declared = project.get("document_types") or []
    statuses = project.get("document_statuses") or []

    duplicates = sorted({item for item in declared if declared.count(item) > 1})
    if duplicates:
        problems.append(f"document_types содержит дубли: {', '.join(duplicates)}")

    declared_set = set(declared)
    used = _used_types(root)
    for doc_type in sorted(used - declared_set):
        problems.append(f"тип {doc_type!r} используется в index.json, но не объявлен")

    rows = _registry_rows(_contract_text(root))
    for doc_type in sorted(declared_set - set(rows)):
        problems.append(f"объявленный тип {doc_type!r} отсутствует в таблице §5.5")
    for doc_type in sorted(set(rows) - declared_set):
        problems.append(f"тип {doc_type!r} есть в §5.5, но не объявлен в paths.yaml")

    for doc_type in sorted(used):
        if (root / BODIES / f"{doc_type}.json").exists():
            continue
        if "prose-only" not in rows.get(doc_type, ""):
            problems.append(
                f"используемый тип {doc_type!r} без body-схемы и без пометки prose-only"
            )

    for doc_type in sorted(declared_set - used):
        if "Зарезервирован" not in rows.get(doc_type, ""):
            problems.append(f"неиспользуемый тип {doc_type!r} не помечен зарезервированным")

    bodies_dir = root / BODIES
    if bodies_dir.is_dir():
        for schema_file in sorted(bodies_dir.glob("*.json")):
            try:
                schema = json.loads(schema_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                problems.append(f"body-схема {schema_file.name} не парсится: {exc.msg}")
                continue
            if schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
                problems.append(
                    f"body-схема {schema_file.name} не объявляет Draft 2020-12"
                )

    schema_statuses = set(
        json.loads((root / DOC_SCHEMA).read_text(encoding="utf-8"))["properties"]["status"]["enum"]
    )
    if schema_statuses != set(statuses):
        problems.append(
            "enum статусов document.schema.json не совпадает с paths.yaml: "
            f"{sorted(schema_statuses)} != {sorted(set(statuses))}"
        )
    if _contract_statuses(_contract_text(root)) != set(statuses):
        problems.append("enum статусов §2.3 не совпадает с paths.yaml")

    return problems


class DocTypeRegistryTest(unittest.TestCase):
    def make_root(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        for relative in (PATHS, INDEX, CONTRACT, DOC_SCHEMA):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / relative, target)
        shutil.copytree(ROOT / BODIES, root / BODIES)
        return root

    def test_repository_registry_is_consistent(self):
        self.assertEqual(registry_problems(ROOT), [])

    def test_duplicate_document_type_is_rejected(self):
        root = self.make_root()
        paths = root / PATHS
        paths.write_text(
            paths.read_text(encoding="utf-8").replace(
                "  document_types:\n", "  document_types:\n    - entity\n", 1
            ),
            encoding="utf-8",
        )
        problems = registry_problems(root)
        self.assertTrue(any("дубли" in problem and "entity" in problem for problem in problems), problems)

    def test_undeclared_used_type_is_rejected(self):
        root = self.make_root()
        index = root / INDEX
        data = json.loads(index.read_text(encoding="utf-8"))
        data["documents"][0]["type"] = "mystery-type"
        index.write_text(json.dumps(data), encoding="utf-8")
        problems = registry_problems(root)
        self.assertTrue(any("mystery-type" in problem for problem in problems), problems)

    def test_missing_contract_row_is_rejected(self):
        root = self.make_root()
        contract = root / CONTRACT
        text = contract.read_text(encoding="utf-8")
        kept = [line for line in text.splitlines() if not line.startswith("| `runbook` |")]
        contract.write_text("\n".join(kept) + "\n", encoding="utf-8")
        problems = registry_problems(root)
        self.assertTrue(any("runbook" in problem for problem in problems), problems)

    def test_missing_body_schema_without_prose_only_is_rejected(self):
        root = self.make_root()
        (root / BODIES / "decision.json").unlink()
        problems = registry_problems(root)
        self.assertTrue(
            any("decision" in problem and "prose-only" in problem for problem in problems),
            problems,
        )

    def test_invalid_body_schema_is_rejected(self):
        root = self.make_root()
        (root / BODIES / "glossary.json").write_text("{\n  \"has_terms\": true,\n", encoding="utf-8")
        problems = registry_problems(root)
        self.assertTrue(any("glossary.json" in problem for problem in problems), problems)

    def test_status_enum_mismatch_is_rejected(self):
        root = self.make_root()
        schema_file = root / DOC_SCHEMA
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
        schema["properties"]["status"]["enum"].append("rejected")
        schema_file.write_text(json.dumps(schema), encoding="utf-8")
        problems = registry_problems(root)
        self.assertTrue(any("статус" in problem for problem in problems), problems)


if __name__ == "__main__":
    unittest.main()
