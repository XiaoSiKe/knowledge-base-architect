#!/usr/bin/env python3
"""Lightweight Markdown quality check for knowledge-base-architect outputs."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote


CHATBOT_PHRASES = (
    "当然可以",
    "没问题",
    "希望对你有帮助",
    "如果你愿意",
    "让我们深入",
    "综上所述",
)

PLACEHOLDERS = ("[TODO", "TODO:", "TBD", "lorem ipsum")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")


def _content_lines(text: str) -> tuple[list[tuple[int, str]], int | None]:
    """Return non-fenced lines and the start of an unclosed fence, if any."""

    lines: list[tuple[int, str]] = []
    fence: tuple[str, int] | None = None
    fence_start: int | None = None

    for number, raw in enumerate(text.splitlines(), 1):
        match = FENCE_RE.match(raw)
        if fence is not None:
            if match:
                marker = match.group(1)
                if marker[0] == fence[0] and len(marker) >= fence[1]:
                    fence = None
                    fence_start = None
            continue

        if match:
            marker = match.group(1)
            fence = (marker[0], len(marker))
            fence_start = number
            continue

        lines.append((number, raw))

    return lines, fence_start


def _link_destination(raw_target: str) -> str:
    """Extract a Markdown link destination without its optional title."""

    raw_target = raw_target.strip()
    if raw_target.startswith("<"):
        closing = raw_target.find(">")
        if closing != -1:
            return raw_target[1:closing].strip()
    return raw_target.split(maxsplit=1)[0] if raw_target else ""


def audit(path: Path) -> tuple[list[str], list[str]]:
    text = path.read_text(encoding="utf-8")
    errors: list[str] = []
    warnings: list[str] = []

    if not text.strip():
        errors.append("文件为空")
        return errors, warnings

    content_lines, unclosed_fence = _content_lines(text)
    content = "\n".join(raw for _, raw in content_lines)
    if unclosed_fence is not None:
        errors.append(f"第 {unclosed_fence} 行代码围栏未闭合")

    for placeholder in PLACEHOLDERS:
        if placeholder.lower() in content.lower():
            errors.append(f"包含未完成占位符：{placeholder}")

    headings: list[tuple[int, int, str]] = []
    seen_lines: dict[str, int] = {}

    for number, raw in content_lines:
        stripped = raw.strip()
        match = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", stripped)
        if match:
            headings.append((number, len(match.group(1)), match.group(2).strip()))

        if len(stripped) > 260 and not stripped.startswith(("http", "|")):
            warnings.append(f"第 {number} 行较长，建议拆分")

        if len(stripped) >= 16 and not stripped.startswith(("#", "|", "-", ">")):
            seen_lines[stripped] = seen_lines.get(stripped, 0) + 1

    for (_, previous, _), (line, current, _) in zip(headings, headings[1:]):
        if current > previous + 1:
            errors.append(f"第 {line} 行标题层级跳跃：H{previous} → H{current}")

    h1_count = sum(level == 1 for _, level, _ in headings)
    if h1_count > 1:
        warnings.append(f"一级标题较多：{h1_count} 个")

    heading_counts: dict[str, int] = {}
    for _, _, title in headings:
        normalized = re.sub(r"\s+", " ", title).casefold()
        heading_counts[normalized] = heading_counts.get(normalized, 0) + 1
    duplicate_headings = sum(count > 1 for count in heading_counts.values())
    if duplicate_headings:
        warnings.append(f"发现 {duplicate_headings} 个重复标题")

    duplicate_lines = [line for line, count in seen_lines.items() if count > 1]
    if duplicate_lines:
        warnings.append(f"发现 {len(duplicate_lines)} 条重复长句")

    for phrase in CHATBOT_PHRASES:
        if phrase in content:
            warnings.append(f"包含聊天或套话：{phrase}")

    bold_count = len(re.findall(r"\*\*[^*]+\*\*", content))
    if bold_count > 16:
        warnings.append(f"粗体较多：{bold_count} 处")

    for raw_target in re.findall(r"\[[^\]]*\]\(([^)]*)\)", content):
        target = _link_destination(raw_target)
        if not target:
            errors.append("包含空链接目标")
            continue
        normalized_target = target.casefold()
        if normalized_target.startswith(
            ("http://", "https://", "#", "mailto:", "tel:", "data:")
        ):
            continue
        local_target = target.split("#", 1)[0].split("?", 1)[0]
        candidate = (path.parent / unquote(local_target)).resolve()
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
