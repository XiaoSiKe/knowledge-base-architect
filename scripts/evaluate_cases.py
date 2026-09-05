#!/usr/bin/env python3
"""Validate, inspect, and score behavioral evaluation cases."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = ROOT / "evals" / "cases.json"
ALLOWED_MODES = {
    "standard",
    "content-architecture",
    "source-intake",
    "style-calibration",
    "persistent-style",
    "tutorial",
    "research",
    "zhihu",
}
CASE_FIELDS = {
    "id",
    "title",
    "request",
    "source_summary",
    "fixture",
    "expected_activation",
    "expected_modes",
    "required_references",
    "must_preserve",
    "must_avoid",
    "success_criteria",
    "metrics",
}
LIST_FIELDS = {
    "expected_modes",
    "required_references",
    "must_preserve",
    "must_avoid",
    "success_criteria",
    "metrics",
}


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any, allow_empty: bool = False) -> bool:
    return (
        isinstance(value, list)
        and (allow_empty or bool(value))
        and all(_nonempty_string(item) for item in value)
    )


def _repo_file(repo_root: Path, relative_path: str) -> Path | None:
    path = Path(relative_path)
    if path.is_absolute():
        return None
    resolved_root = repo_root.resolve()
    resolved_path = (resolved_root / path).resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError:
        return None
    return resolved_path


def load_json(path: Path) -> tuple[Any | None, list[str]]:
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except FileNotFoundError:
        return None, [f"文件不存在：{path}"]
    except json.JSONDecodeError as error:
        return None, [f"JSON 无效：第 {error.lineno} 行第 {error.colno} 列"]


def validate_suite(data: Any, repo_root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["评测套件根节点必须是 JSON 对象"]
    if data.get("schema_version") != 1:
        errors.append("schema_version 必须为 1")
    if not _nonempty_string(data.get("suite_id")):
        errors.append("suite_id 必须是非空字符串")

    policy = data.get("pass_policy")
    if not isinstance(policy, dict):
        errors.append("pass_policy 必须是对象")
    else:
        minimum_score = policy.get("minimum_metric_score")
        minimum_average = policy.get("minimum_average")
        max_failures = policy.get("max_critical_failures")
        if isinstance(minimum_score, bool) or not isinstance(minimum_score, int) or not 0 <= minimum_score <= 2:
            errors.append("minimum_metric_score 必须是 0 到 2 的整数")
        if isinstance(minimum_average, bool) or not isinstance(minimum_average, (int, float)) or not 0 <= minimum_average <= 2:
            errors.append("minimum_average 必须是 0 到 2 的数字")
        if isinstance(max_failures, bool) or not isinstance(max_failures, int) or max_failures < 0:
            errors.append("max_critical_failures 必须是非负整数")

    rubric = data.get("rubric")
    if not isinstance(rubric, dict) or not rubric:
        errors.append("rubric 必须是非空对象")
        metric_names: set[str] = set()
    else:
        metric_names = set(rubric)
        for metric, description in rubric.items():
            if not _nonempty_string(metric) or not _nonempty_string(description):
                errors.append("rubric 的指标名称和说明必须是非空字符串")

    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        errors.append("cases 必须是非空数组")
        return errors

    seen_ids: set[str] = set()
    for index, case in enumerate(cases):
        prefix = f"cases[{index}]"
        if not isinstance(case, dict):
            errors.append(f"{prefix} 必须是对象")
            continue
        missing = sorted(CASE_FIELDS - set(case))
        if missing:
            errors.append(f"{prefix} 缺少字段：{', '.join(missing)}")
        case_id = case.get("id")
        if not _nonempty_string(case_id):
            errors.append(f"{prefix}.id 必须是非空字符串")
        elif case_id in seen_ids:
            errors.append(f"{prefix}.id 重复：{case_id}")
        else:
            seen_ids.add(case_id)
        for field in ("title", "request", "source_summary", "fixture"):
            if not _nonempty_string(case.get(field)):
                errors.append(f"{prefix}.{field} 必须是非空字符串")
        if not isinstance(case.get("expected_activation"), bool):
            errors.append(f"{prefix}.expected_activation 必须是布尔值")
        for field in LIST_FIELDS:
            allow_empty = field in {"expected_modes", "required_references", "must_avoid"}
            if not _string_list(case.get(field), allow_empty=allow_empty):
                errors.append(f"{prefix}.{field} 必须是字符串数组")

        modes = set(case.get("expected_modes", []))
        unknown_modes = sorted(modes - ALLOWED_MODES)
        if unknown_modes:
            errors.append(f"{prefix}.expected_modes 包含未知模式：{', '.join(unknown_modes)}")
        if case.get("expected_activation") is False and modes:
            errors.append(f"{prefix} 不触发时 expected_modes 必须为空")

        metrics = set(case.get("metrics", []))
        unknown_metrics = sorted(metrics - metric_names)
        if unknown_metrics:
            errors.append(f"{prefix}.metrics 包含未知指标：{', '.join(unknown_metrics)}")
        if "activation" not in metrics:
            errors.append(f"{prefix}.metrics 必须包含 activation")

        for reference in case.get("required_references", []):
            reference_path = _repo_file(repo_root, reference)
            if reference_path is None or not reference_path.is_file():
                errors.append(f"{prefix}.required_references 不存在：{reference}")
        fixture = case.get("fixture")
        if _nonempty_string(fixture):
            fixture_path = _repo_file(repo_root, fixture)
            if fixture_path is None or not fixture_path.is_file():
                errors.append(f"{prefix}.fixture 不存在或超出仓库：{fixture}")

    return errors


def validate_results(suite: dict[str, Any], data: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(data, dict):
        return ["评分结果根节点必须是 JSON 对象"]
    if data.get("schema_version") != 1:
        errors.append("结果 schema_version 必须为 1")
    if data.get("suite_id") != suite.get("suite_id"):
        errors.append("结果 suite_id 与评测套件不一致")

    cases_by_id = {case["id"]: case for case in suite["cases"]}
    evaluations = data.get("evaluations")
    if not isinstance(evaluations, list):
        return errors + ["evaluations 必须是数组"]

    seen_ids: set[str] = set()
    for index, evaluation in enumerate(evaluations):
        prefix = f"evaluations[{index}]"
        if not isinstance(evaluation, dict):
            errors.append(f"{prefix} 必须是对象")
            continue
        case_id = evaluation.get("case_id")
        if case_id not in cases_by_id:
            errors.append(f"{prefix}.case_id 不存在：{case_id}")
            continue
        if case_id in seen_ids:
            errors.append(f"{prefix}.case_id 重复：{case_id}")
            continue
        seen_ids.add(case_id)

        expected_metrics = set(cases_by_id[case_id]["metrics"])
        scores = evaluation.get("scores")
        if not isinstance(scores, dict):
            errors.append(f"{prefix}.scores 必须是对象")
        else:
            if set(scores) != expected_metrics:
                errors.append(f"{prefix}.scores 必须且只能包含案例指定指标")
            for metric, score in scores.items():
                if isinstance(score, bool) or not isinstance(score, int) or score not in {0, 1, 2}:
                    errors.append(f"{prefix}.scores.{metric} 必须是 0、1 或 2")

        evidence = evaluation.get("evidence")
        if not isinstance(evidence, dict):
            errors.append(f"{prefix}.evidence 必须是对象")
        else:
            if set(evidence) != expected_metrics:
                errors.append(f"{prefix}.evidence 必须且只能包含案例指定指标")
            for metric, explanation in evidence.items():
                if not _nonempty_string(explanation):
                    errors.append(f"{prefix}.evidence.{metric} 必须包含具体证据")

        critical_failures = evaluation.get("critical_failures")
        if not isinstance(critical_failures, list) or not all(
            _nonempty_string(item) for item in critical_failures
        ):
            errors.append(f"{prefix}.critical_failures 必须是字符串数组")

    missing_cases = sorted(set(cases_by_id) - seen_ids)
    if missing_cases:
        errors.append(f"评分结果缺少案例：{', '.join(missing_cases)}")
    return errors


def score_results(suite: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    policy = suite["pass_policy"]
    minimum_score = policy["minimum_metric_score"]
    minimum_average = policy["minimum_average"]
    case_results = []
    critical_failure_count = 0

    for evaluation in data["evaluations"]:
        scores = list(evaluation["scores"].values())
        average = sum(scores) / len(scores)
        critical_failures = evaluation["critical_failures"]
        critical_failure_count += len(critical_failures)
        passed = (
            min(scores) >= minimum_score
            and average >= minimum_average
            and not critical_failures
        )
        case_results.append(
            {"case_id": evaluation["case_id"], "average": round(average, 2), "passed": passed}
        )

    overall_average = sum(item["average"] for item in case_results) / len(case_results)
    passed = (
        all(item["passed"] for item in case_results)
        and critical_failure_count <= policy["max_critical_failures"]
    )
    return {
        "passed": passed,
        "overall_average": round(overall_average, 2),
        "critical_failure_count": critical_failure_count,
        "cases": case_results,
    }


def generator_input(case: dict[str, Any], repo_root: Path = ROOT) -> dict[str, str]:
    fixture_path = _repo_file(repo_root, case["fixture"])
    if fixture_path is None or not fixture_path.is_file():
        raise ValueError("fixture 不存在或超出仓库")
    return {
        "id": case["id"],
        "title": case["title"],
        "request": case["request"],
        "source_material": fixture_path.read_text(encoding="utf-8"),
    }


def load_valid_suite(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    data, load_errors = load_json(path)
    if load_errors:
        return None, load_errors
    errors = validate_suite(data, path.parent.parent)
    return (data if not errors else None), errors


def main() -> int:
    parser = argparse.ArgumentParser(description="管理知识库架构大师行为评测")
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate", help="验证评测案例定义")
    show_parser = subparsers.add_parser("show", help="查看一个评测案例")
    show_parser.add_argument("case_id")
    show_parser.add_argument("--input-only", action="store_true", help="只显示生成 Agent 可见输入")
    score_parser = subparsers.add_parser("score", help="验证并计算评分结果")
    score_parser.add_argument("results", type=Path)
    args = parser.parse_args()

    suite, suite_errors = load_valid_suite(args.suite)
    if suite_errors:
        for error in suite_errors:
            print(f"ERROR: {error}")
        return 1
    assert suite is not None

    if args.command == "validate":
        print(f"{args.suite}: {len(suite['cases'])} cases, 0 errors")
        return 0

    if args.command == "show":
        case = next((item for item in suite["cases"] if item["id"] == args.case_id), None)
        if case is None:
            print(f"ERROR: 案例不存在：{args.case_id}")
            return 1
        if args.input_only:
            case = generator_input(case, args.suite.parent.parent)
        print(json.dumps(case, ensure_ascii=False, indent=2))
        return 0

    results, load_errors = load_json(args.results)
    if load_errors:
        for error in load_errors:
            print(f"ERROR: {error}")
        return 1
    result_errors = validate_results(suite, results)
    if result_errors:
        for error in result_errors:
            print(f"ERROR: {error}")
        return 1
    summary = score_results(suite, results)
    for item in summary["cases"]:
        status = "PASS" if item["passed"] else "FAIL"
        print(f"{status} {item['case_id']}: {item['average']:.2f}")
    status = "PASS" if summary["passed"] else "FAIL"
    print(
        f"{status} overall: {summary['overall_average']:.2f}, "
        f"critical failures: {summary['critical_failure_count']}"
    )
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
