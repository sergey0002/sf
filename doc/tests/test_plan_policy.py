import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLI = [sys.executable, str(ROOT / "doc/tools/arch/__main__.py")]
sys.path.insert(0, str(ROOT / "doc/tools"))
from arch.plan_policy import evaluate_rules, resolve_plan_policy  # noqa: E402
from arch.project_config import load_project_config  # noqa: E402


def cli(*args):
    return subprocess.run(CLI + list(args), cwd=ROOT, text=True, capture_output=True, check=False)


class PlanPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config, errors = load_project_config(ROOT)
        if errors:
            raise AssertionError(errors)

    def test_config_defaults_match_current_contract(self):
        policy, problems = resolve_plan_policy(self.config, "feature")
        self.assertEqual(problems, [])
        self.assertEqual(policy["tiers"]["micro"]["max_nonempty_lines"], 60)
        self.assertIn("Приёмка", policy["tiers"]["standard"]["required_sections"])
        research, _ = resolve_plan_policy(self.config, "research")
        self.assertIn("Источники", research["tiers"]["standard"]["required_sections"])
        self.assertNotIn("full", research["tiers"])
        scaffold, _ = resolve_plan_policy(self.config, "scaffold")
        self.assertEqual(set(scaffold["tiers"]), {"micro"})

    def test_templates_cover_every_declared_tier(self):
        for type_id in ("feature", "bugfix", "refactor", "docs", "research", "audit", "planning", "jira-incoming", "scaffold", "subtask", "spike", "migration", "incident"):
            policy, problems = resolve_plan_policy(self.config, type_id)
            self.assertEqual(problems, [], type_id)
            for tier, spec in policy["tiers"].items():
                path = self.config.task_conf_root / "types" / type_id / spec["template"]
                text = path.read_text(encoding="utf-8")
                self.assertTrue(text.strip(), path)
                for section in spec["required_sections"]:
                    self.assertIn(section, text, f"{type_id}/{tier} missing {section}")

    def test_plan_policy_command_is_read_only_and_reports_unknown_type(self):
        before = sorted(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if ".git" not in path.parts)
        result = cli("task", "plan-policy", "--type", "research", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)["data"]
        self.assertEqual(data["acceptance"]["profile"], "research")
        self.assertTrue(data["source"]["flow_ignored"])
        after = sorted(path.relative_to(ROOT).as_posix() for path in ROOT.rglob("*") if ".git" not in path.parts)
        self.assertEqual(before, after)
        unknown = cli("task", "plan-policy", "--type", "unknown")
        self.assertEqual(unknown.returncode, 1)
        self.assertIn("unknown", unknown.stderr)

    def test_rules_name_file_section_and_rule(self):
        policy, _ = resolve_plan_policy(self.config, "research")
        problems = evaluate_rules("# План\n## Вопросы\n- один\n", policy, case_count=1)
        self.assertTrue(any("Источники" in item and "section_min_items" in item for item in problems))
        audit, _ = resolve_plan_policy(self.config, "audit")
        problems = evaluate_rules("## Findings\n\n| ID | Text |\n|---|---|\n| 1 | x |\n", audit)
        self.assertTrue(any("Severity" in item and "table_column" in item for item in problems))
        problems = evaluate_rules("## Findings\n\n| Severity |\n|---|\n| high |\n## Границы покрытия\n- граница\n", audit, case_count=1)
        self.assertEqual(problems, [])

    def test_task_conf_scan_passes_and_detects_mismatch(self):
        result = cli("scan", "--scope", "task-conf", "--brief")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        from arch.plan_policy import task_conf_integrity
        problems = task_conf_integrity(self.config, ["feature"])
        self.assertTrue(any("paths.yaml" in item for item in problems))

    def test_paths_allow_policy_files(self):
        result = cli("docs", "paths", "--check")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
