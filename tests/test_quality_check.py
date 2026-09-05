from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_quality_module():
    path = ROOT / "scripts" / "quality_check.py"
    spec = importlib.util.spec_from_file_location("quality_check_under_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QualityCheckTests(unittest.TestCase):
    def setUp(self):
        self.module = load_quality_module()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def audit(self, text: str):
        path = self.root / "document.md"
        path.write_text(text, encoding="utf-8")
        return self.module.audit(path)

    def test_ignores_examples_inside_code_fences(self):
        errors, warnings = self.audit(
            "# 标题\n\n```md\n### 跳级标题\n[示例](missing.md)\nTODO: 示例\n```\n"
        )
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_reports_unclosed_code_fence(self):
        errors, _warnings = self.audit("# 标题\n\n```text\n未结束\n")
        self.assertTrue(any("代码围栏未闭合" in error for error in errors))

    def test_reports_heading_jump(self):
        errors, _warnings = self.audit("# 标题\n\n### 跳过二级标题\n")
        self.assertTrue(any("标题层级跳跃" in error for error in errors))

    def test_reports_empty_and_missing_links(self):
        errors, _warnings = self.audit("# 标题\n\n[空]()\n\n[缺失](missing.md)\n")
        self.assertIn("包含空链接目标", errors)
        self.assertTrue(any("相对链接不存在" in error for error in errors))

    def test_accepts_percent_encoded_local_link(self):
        (self.root / "有 空格.md").write_text("# 文件\n", encoding="utf-8")
        errors, _warnings = self.audit(
            '# 标题\n\n[文件](%E6%9C%89%20%E7%A9%BA%E6%A0%BC.md "可选标题")\n'
        )
        self.assertEqual(errors, [])

    def test_accepts_angle_bracket_link_with_spaces(self):
        (self.root / "有 空格.md").write_text("# 文件\n", encoding="utf-8")
        errors, _warnings = self.audit('# 标题\n\n[文件](<有 空格.md> "可选标题")\n')
        self.assertEqual(errors, [])

    def test_warns_about_duplicate_headings(self):
        errors, warnings = self.audit("# 标题\n\n## 重复\n\n## 重复\n")
        self.assertEqual(errors, [])
        self.assertTrue(any("重复标题" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
