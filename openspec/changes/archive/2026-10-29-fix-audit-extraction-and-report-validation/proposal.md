## Why

自审发现普通 argparse 入口的参数遗漏、循环与异常表达式子树遗漏，以及报告检查器拒绝方法文档展示的多行因果链。这些问题会减少审计证据或拒绝格式合法的报告。

## What Changes

- 提取普通 ArgumentParser 入口及其参数，保留子命令行为。
- 遍历 for、while、raise 的表达式子树，保留现有门禁事实。
- 校验完整因果链字段，支持多行内容并限制在当前字段内。
- 为三项缺陷添加最小回归检查；不将静态候选解释为过度门禁。

## Capabilities

### New Capabilities

- `audit-report-validation`: 因果链字段的多行证据标记检查。

### Modified Capabilities

- `python-fact-extraction`: 明确普通 argparse 命令提取和循环、异常表达式的事实遍历。

## Impact

影响两个标准库 Python 脚本及其回归检查，不增加依赖，不执行目标代码。事实 JSON 保持现有 schema，新增原先遗漏的事实。不在本次合入外部 README 补丁、发布版本或修改仓库元数据。
