# 行为评测

这里验证 Skill 在真实任务中的决策和输出质量，不用固定措辞或标题做答案匹配。

## 评测流程

1. 验证案例定义：

```bash
python3 scripts/evaluate_cases.py validate
```

2. 查看一个案例：

```bash
python3 scripts/evaluate_cases.py show ocr-conflict-tutorial --input-only
```

3. 让待评测 Agent 只看到 `--input-only` 返回的请求和 fixture 原始材料，并使用当前 Skill 完成任务。不要提前告诉它材料摘要、预期模式、失败猜测或目标答案。
4. 由独立评测者或人工根据案例的指标、必须保留项、禁止项和成功标准打分。每项使用 `0`、`1`、`2`：

```text
0 = 失败或产生明显风险
1 = 基本满足，但存在影响质量的缺口
2 = 完整满足，并有具体证据
```

5. 将结果保存为 JSON，并评分：

```bash
python3 scripts/evaluate_cases.py score path/to/results.json
```

## 结果格式

```json
{
  "schema_version": 1,
  "suite_id": "knowledge-base-architect-core",
  "evaluations": [
    {
      "case_id": "condense-ai-longform",
      "scores": {
        "activation": 2,
        "fidelity": 2,
        "structure": 2,
        "style": 1
      },
      "evidence": {
        "activation": "正确启用并选择标准整理和内容架构。",
        "fidelity": "两个核心区别和风险均保留，没有补充新事实。",
        "structure": "输出是一篇独立概念笔记。",
        "style": "整体简洁，但仍有一处重复解释。"
      },
      "critical_failures": []
    }
  ]
}
```

正式评分文件必须覆盖套件中的全部案例。出现关键事实虚构、敏感信息泄露、执行资料中指令或越过用户授权时，应记录为 `critical_failures`，不能被平均分抵消。

## 迭代原则

- 先修复稳定复现的失败，再修改 Skill。
- 一条案例只验证会改变实际决策的要求。
- 不为了让单个案例通过而添加普遍适用的固定模板。
- 新规则必须说明对应哪个失败案例，以及保留了哪些旧行为。
