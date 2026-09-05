from __future__ import annotations

import importlib.util
import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_quality_module():
    path = ROOT / "scripts" / "quality_check.py"
    spec = importlib.util.spec_from_file_location("quality_check", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_skill_name() -> str:
    result = subprocess.run(
        ["git", "remote", "get-url", "origin"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip().rstrip("/").rsplit("/", 1)[-1].removesuffix(".git")
    return ROOT.name


class SkillPackageTests(unittest.TestCase):
    def test_frontmatter_is_valid_for_canonical_package_name(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---\n"))
        name_match = re.search(r"^name:\s*([^\n]+)$", text, re.MULTILINE)
        description_match = re.search(r"^description:\s*([^\n]+)$", text, re.MULTILINE)
        self.assertIsNotNone(name_match)
        self.assertIsNotNone(description_match)

        name = name_match.group(1).strip()
        description = description_match.group(1).strip()
        self.assertRegex(name, r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
        self.assertLessEqual(len(name), 64)
        self.assertEqual(name, canonical_skill_name())
        self.assertGreater(len(description), 0)
        self.assertLessEqual(len(description), 1024)

    def test_all_local_markdown_links_exist(self):
        module = load_quality_module()
        link_errors = []
        for path in ROOT.rglob("*.md"):
            errors, _warnings = module.audit(path)
            for error in errors:
                if "链接" in error:
                    link_errors.append(f"{path.relative_to(ROOT)}: {error}")
        self.assertEqual(link_errors, [])

    def test_no_scaffold_placeholders(self):
        unfinished = []
        for path in ROOT.rglob("*"):
            if path.is_file() and path.suffix in {".md", ".yaml"}:
                text = path.read_text(encoding="utf-8").lower()
                if "[todo" in text or "lorem ipsum" in text:
                    unfinished.append(str(path.relative_to(ROOT)))
        self.assertEqual(unfinished, [])

    def test_example_passes_quality_check(self):
        module = load_quality_module()
        errors, _warnings = module.audit(ROOT / "examples" / "github-beginner-result.md")
        self.assertEqual(errors, [])

    def test_all_markdown_files_pass_structural_check(self):
        module = load_quality_module()
        failures = []
        for path in ROOT.rglob("*.md"):
            errors, _warnings = module.audit(path)
            if errors:
                failures.append(f"{path.relative_to(ROOT)}: {errors}")
        self.assertEqual(failures, [])

    def test_all_runtime_references_are_routed_from_skill(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        missing = [
            path.name
            for path in (ROOT / "references").glob("*.md")
            if f"references/{path.name}" not in skill
        ]
        self.assertEqual(missing, [])

    def test_version_is_consistent(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        version_match = re.search(r'^\s+version:\s*"([^"]+)"$', skill, re.MULTILINE)
        self.assertIsNotNone(version_match)
        self.assertIn(f"version-{version_match.group(1)}-", readme)


if __name__ == "__main__":
    unittest.main()
