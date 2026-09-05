#!/usr/bin/env python3
"""Lightweight Markdown quality check for knowledge-base-architect outputs."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


CHATBOT_PHRASES = (
    "当然可以",
    "没问题",
    "希望对你有帮助",
    "如果你愿意",
    "让我们深入",
    "综上所述",
)

PLACEHOLDERS = ("[TODO", "TODO:", "TBD", "lorem ipsum")


def audit(path: Path) -> tuple[list[str], list[str]]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []

    if not text.strip():
        errors.append("文件为空")
        return errors, warnings

    for placeholder in PLACEHOLDERS:
        if placeholder.lower() in text.lower():
            errors.append(f"包含未完成占位符：{placeholder}")

    headings = []
    in_fence = False
    seen_lines: dict[str, int] = {}

    for number, raw in enumerate(text.splitlines(), 1):
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        match = re.match(r"^(#{1,6})\s+\S", stripped)
        if match:
            headings.append((number, len(match.group(1))))

        if len(stripped) > 260 and not stripped.startswith(("http", "|")):
            warnings.append(f"第 {number} 行较长，建议拆分")

        if len(stripped) >= 16 and not stripped.startswith(("#", "|", "-", ">")):
            seen_lines[stripped] = seen_lines.get(stripped, 0) + 1

    for (_, previous), (line, current) in zip(headings, headings[1:]):
        if current > previous + 1:
            errors.append(f"第 {line} 行标题层级跳跃：H{previous} → H{current}")

    duplicate_lines = [line for line, count in seen_lines.items() if count > 1]
    if duplicate_lines:
        warnings.append(f"发现 {len(duplicate_lines)} 条重复长句")

    for phrase in CHATBOT_PHRASES:
        if phrase in text:
            warnings.append(f"包含聊天或套话：{phrase}")

    bold_count = len(re.findall(r"\*\*[^*]+\*\*", text))
    if bold_count > 16:
        warnings.append(f"粗体较多：{bold_count} 处")

    for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        candidate = (path.parent / target.split("#", 1)[0]).resolve()
        if not candidate.exists():
            errors.append(f"相对链接不存在：{target}")

    return errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="检查知识库 Markdown 的结构和常见 AI 写作问题")
    parser.add_argument("paths", nargs="+", type=Path)
    parser.add_argument("--strict", action="store_true", help="将警告视为失败")
    args = parser.parse_args()

    total_errors = 0
    total_warnings = 0
    for path in args.paths:
        if not path.is_file():
            print(f"ERROR {path}: 文件不存在")
            total_errors += 1
            continue
        errors, warnings = audit(path)
        total_errors += len(errors)
        total_warnings += len(warnings)
        print(f"{path}: {len(errors)} errors, {len(warnings)} warnings")
        for message in errors:
            print(f"  ERROR: {message}")
        for message in warnings:
            print(f"  WARN: {message}")

    if total_errors or (args.strict and total_warnings):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
