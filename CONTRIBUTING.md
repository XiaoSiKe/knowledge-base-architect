# 参与贡献

感谢你改进知识库架构大师。

## 可以贡献什么？

- 更准确的触发描述
- 更可靠的多来源摄取、OCR 不确定性和来源冲突处理
- 更好的个人风格校准方法
- 能让读者完成真实结果的小白教程流程
- 研究、知乎或其他平台的独立参考模块
- 能发现真实质量问题的检查规则
- 简短、可复现的前后对比示例

## 提交原则

1. 不削弱“用户个人风格优先”。
2. 不把可选方法变成所有任务的强制流程。
3. 不添加虚构来源、案例或测试结果。
4. 大段条件化内容放入 `references/`，保持 `SKILL.md` 精简。
5. 新脚本只使用标准库，或清楚说明依赖。
6. 新增模式必须有明确触发边界，并从 `SKILL.md` 路由到按需参考文件。
7. 新质量规则必须包含至少一个通过用例和一个失败用例。

## 提交前验证

```bash
python3 scripts/quality_check.py --strict examples/github-beginner-result.md README.md SKILL.md references/*.md
python3 -m unittest discover -s tests -v
```
